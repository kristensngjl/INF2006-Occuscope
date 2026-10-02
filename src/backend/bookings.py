"""Project student accounts and discussion-room reservations (not official SIT RBS)."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

SGT = timezone(timedelta(hours=8))
COOKIE = "occuscope_session"
SESSION_SECONDS = 8 * 3600


def now_sgt():
    return datetime.now(SGT)


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def password_matches(password, encoded):
    try:
        _, _, salt, _ = encoded.split("$")
        return hmac.compare_digest(password_hash(password, salt), encoded)
    except (ValueError, TypeError):
        return False


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)


class SlotBookingInput(BaseModel):
    location_id: str = Field(min_length=1, max_length=100)
    slots: list[str] = Field(min_length=1, max_length=8)


def create_router(path, parse_time):
    router = APIRouter()
    migration_lock = threading.Lock()
    migrated = False
    attempts = defaultdict(deque)
    attempts_lock = threading.Lock()
    dummy_hash = password_hash("dummy-login-password")

    @contextmanager
    def database():
        nonlocal migrated
        conn = None
        try:
            # Never silently create a new empty campus database.
            conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=rw", uri=True, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            with migration_lock:
                if not migrated:
                    conn.executescript(Path(__file__).with_name("booking_schema.sql").read_text(encoding="utf-8"))
                    migrated = True
            yield conn
        except sqlite3.OperationalError:
            raise HTTPException(503, "Booking database unavailable. Check the backend database and restart after rebuilding it.") from None
        finally:
            if conn is not None:
                conn.close()

    def write_guard(request):
        # A cross-origin HTML form cannot supply this header; no CORS is enabled.
        if request.headers.get("x-occuscope-request") != "1":
            raise HTTPException(403, "Reload this page before trying again.")

    def throttle(request):
        address = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with attempts_lock:
            for key in list(attempts):
                if not attempts[key] or attempts[key][-1] <= now - 60:
                    del attempts[key]
            bucket = attempts[address]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= 10:
                raise HTTPException(429, "Too many sign-in attempts. Try again in a minute.")
            bucket.append(now)

    def email_address(value):
        email = value.strip().lower()
        if not re.fullmatch(r"(?:2500|2600)(?!000)[0-9]{3}@sit\.singaporetech\.edu\.sg", email):
            raise HTTPException(422, "Use your demo student email: IDs 2500001–2500999 or 2600001–2600999, followed by @sit.singaporetech.edu.sg.")
        return email

    def session_digest(request):
        return hashlib.sha256(request.cookies.get(COOKIE, "").encode()).hexdigest()

    def student(conn, request):
        row = conn.execute("""SELECT u.user_id,u.email,p.student_id,p.display_name,p.is_demo FROM student_session s
            JOIN app_user u ON u.user_id=s.user_id
            JOIN student_profile p ON p.user_id=u.user_id
            WHERE s.token_hash=? AND s.expires_at>? AND u.role='student'""",
            (session_digest(request), int(time.time()))).fetchone()
        if row is None:
            raise HTTPException(401, "Sign in to book a discussion room.")
        return dict(row)

    def start_session(conn, request, response, user_id):
        token = secrets.token_urlsafe(32)
        conn.execute("DELETE FROM student_session WHERE expires_at<=? OR token_hash=?", (int(time.time()), session_digest(request)))
        conn.execute("INSERT INTO student_session VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, int(time.time()) + SESSION_SECONDS))
        response.set_cookie(COOKIE, token, httponly=True, secure=os.getenv("COOKIE_SECURE", "0") == "1", samesite="strict", max_age=SESSION_SECONDS, path="/")
        response.headers["Cache-Control"] = "no-store"

    @router.post("/auth/login")
    def login(body: Credentials, request: Request, response: Response):
        write_guard(request)
        throttle(request)
        email = email_address(body.email)
        with database() as conn, conn:
            row = conn.execute("""SELECT u.user_id,u.email,c.password_hash,p.student_id,p.display_name,p.is_demo FROM app_user u
                JOIN student_credential c ON u.user_id=c.user_id
                JOIN student_profile p ON u.user_id=p.user_id WHERE u.email=? AND u.role='student'""", (email,)).fetchone()
            valid = password_matches(body.password, row["password_hash"] if row else dummy_hash)
            if row is None or not valid:
                raise HTTPException(401, "Email or password is incorrect.")
            start_session(conn, request, response, row["user_id"])
            return {k:row[k] for k in ("user_id","email","student_id","display_name","is_demo")}

    @router.get("/auth/me")
    def me(request: Request, response: Response):
        response.headers["Cache-Control"] = "no-store"
        with database() as conn:
            return student(conn, request)

    @router.post("/auth/logout")
    def logout(request: Request, response: Response):
        write_guard(request)
        with database() as conn, conn:
            conn.execute("DELETE FROM student_session WHERE token_hash=?", (session_digest(request),))
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict", secure=os.getenv("COOKIE_SECURE", "0") == "1")
        return {"ok":True}

    def room(conn, location_id):
        row = conn.execute("SELECT * FROM location WHERE location_id=?", (location_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Room not found.")
        if row["type"] != "discussion_room":
            raise HTTPException(422, "Only discussion rooms can be booked. Study spaces and food courts are walk-in only.")
        return row

    def conflicts(conn, location_id, start, end, user_id=None):
        params = [end, start, location_id]
        owner = ""
        if user_id:
            owner = " OR user_id=?"
            params.append(user_id)
        reserved = conn.execute("""SELECT 1 FROM room_booking WHERE status='confirmed'
            AND start_time<? AND end_time>? AND (location_id=?""" + owner + ") LIMIT 1", params).fetchone()
        event = conn.execute("""SELECT 1 FROM event WHERE location_id=?
            AND julianday(start_time)<julianday(?) AND julianday(end_time)>julianday(?) LIMIT 1""", (location_id,end,start)).fetchone()
        return bool(reserved or event)

    def allowance(conn, user_id, instant):
        monday = instant.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=instant.weekday())
        end = monday + timedelta(days=7)
        used = 0
        for row in conn.execute("SELECT start_time,end_time FROM room_booking WHERE user_id=? AND status='confirmed' AND start_time<? AND end_time>?", (user_id,end.isoformat(),monday.isoformat())):
            used += int((min(datetime.fromisoformat(row['end_time']),end)-max(datetime.fromisoformat(row['start_time']),monday)).total_seconds() / 60)
        return {"week_start":monday.date().isoformat(),"week_end":(end-timedelta(days=1)).date().isoformat(),
                "limit_minutes":240,"used_minutes":used,"remaining_minutes":max(0,240-used)}

    @router.get("/bookings/availability")
    def availability(location_id: str, date: str, request: Request):
        try:
            day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=SGT)
        except ValueError:
            raise HTTPException(422, "Choose a valid booking date.") from None
        now = now_sgt()
        if not now.date() <= day.date() <= (now + timedelta(days=14)).date():
            raise HTTPException(422, "Choose today or a date within the next 14 days.")
        with database() as conn:
            room(conn,location_id)
            user = student(conn,request) if request.cookies.get(COOKIE) else None
            weekly = allowance(conn,user['user_id'],day) if user else None
            slots=[]
            for half_hour in range(16,40):
                start=day+timedelta(minutes=30*half_hour)
                end=start+timedelta(minutes=30)
                slots.append({"start_time":start.isoformat(),"end_time":end.isoformat(),
                    "available":start>now and not conflicts(conn,location_id,start.isoformat(),end.isoformat(),user["user_id"] if user else None)})
        return {"slots":slots,"timezone":"Asia/Singapore","weekly_allowance":weekly}

    @router.post("/bookings", status_code=201)
    def book(body: SlotBookingInput, request: Request):
        write_guard(request)
        starts = [parse_time(value,"slots") for value in body.slots]
        if len(set(starts)) != len(starts):
            raise HTTPException(422,"Select each time block only once.")
        intervals = [(start,start+timedelta(minutes=30)) for start in sorted(starts)]
        now=now_sgt()
        for start,end in intervals:
            if start<=now or start.date()>(now+timedelta(days=14)).date():
                raise HTTPException(422,"Book a future slot within the next 14 days.")
            if (start.date()!=end.date() or start.hour<8 or end.hour>20 or (end.hour==20 and end.minute!=0)
                or any(t.minute not in (0,30) or t.second or t.microsecond for t in (start,end))
                or not timedelta(minutes=30)<=end-start<=timedelta(minutes=240)):
                raise HTTPException(422,"Choose 30-minute blocks between 08:00 and 20:00 SGT, within your 240-minute weekly limit.")
        results=[]
        with database() as conn, conn:
            # Quota checks, conflict checks, and all blocks commit together.
            conn.execute("BEGIN IMMEDIATE")
            user=student(conn,request)
            room(conn,body.location_id)
            requested={}
            for start,end in intervals:
                weekly=allowance(conn,user['user_id'],start)
                key=weekly['week_start']
                requested[key]=requested.get(key,0)+int((end-start).total_seconds()/60)
                if requested[key]>weekly['remaining_minutes']:
                    raise HTTPException(409,f"Only {weekly['remaining_minutes']} minutes remain for the week starting {key} (240 minutes per week).")
                if conflicts(conn,body.location_id,start.isoformat(),end.isoformat(),user['user_id']):
                    raise HTTPException(409,"A selected block is no longer available or overlaps your other booking. Refresh and select again.")
            for start,end in intervals:
                booking_id=secrets.token_hex(16)
                conn.execute("INSERT INTO room_booking VALUES (?,?,?,?,?,'confirmed',?)",
                    (booking_id,user['user_id'],body.location_id,start.isoformat(),end.isoformat(),now.isoformat()))
                results.append({"booking_id":booking_id,"location_id":body.location_id,"start_time":start.isoformat(),"end_time":end.isoformat(),"status":"confirmed"})
        return {"bookings":results,"booked_minutes":len(results)*30}

    @router.get("/bookings/mine")
    def mine(request: Request, response: Response):
        response.headers["Cache-Control"]="no-store"
        with database() as conn:
            user=student(conn,request)
            return [dict(r) for r in conn.execute("""SELECT r.booking_id,r.location_id,l.name,l.building_id,
                r.start_time,r.end_time,r.status FROM room_booking r JOIN location l ON l.location_id=r.location_id
                WHERE r.user_id=? ORDER BY r.start_time DESC""", (user["user_id"],))]

    @router.post("/bookings/{booking_id}/cancel")
    def cancel(booking_id: str, request: Request):
        write_guard(request)
        with database() as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            user=student(conn,request)
            row=conn.execute("SELECT * FROM room_booking WHERE booking_id=? AND user_id=?", (booking_id,user["user_id"])).fetchone()
            if row is None:
                raise HTTPException(404,"Booking not found.")
            if row["status"]=="cancelled":
                return {"ok":True}
            if datetime.fromisoformat(row["start_time"])<=now_sgt():
                raise HTTPException(409,"Only upcoming bookings can be cancelled.")
            conn.execute("UPDATE room_booking SET status='cancelled' WHERE booking_id=?", (booking_id,))
        return {"ok":True}

    return router
