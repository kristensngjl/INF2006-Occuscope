#!/usr/bin/env python3
"""Scalability and resilience test for the deployed Occuscope API (Kristen).

Standard library only, so it runs in AWS CloudShell with no installs:

    python3 tests/load_test.py https://<api-id>.execute-api.us-east-1.amazonaws.com

Phases
  A  steady load   10 parallel users for 60 s on the heaviest read (map at a time).
                   Expect: all 200, no 5xx, stable latency (Lambda scales out).
  B  spike         60 parallel users for 15 s on /api/locations, above the
                   50 req/s stage limit. Expect: some 429 from API Gateway
                   throttling, no 5xx (the app degrades instead of crashing).
  C  auth throttle 30 rapid calls to /api/auth/me (route limit 2 req/s, burst 5).
                   Expect: 401 (not signed in) for allowed calls, 429 for the rest.
  D  persistence   (only with --persistence; needs the AWS CLI, i.e. CloudShell)
                   sign in, book one future slot, force a cold start of
                   crowdmap-bookings, then check the booking is still there and
                   cancel it. Expect: booking survives the restart.

The chatbot route is deliberately NOT load-tested (protects the Groq free quota).
Output is printed and saved with the API host replaced by <API_URL>.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

SGT = timezone(timedelta(hours=8))
DEMO_EMAIL = "2500123@sit.singaporetech.edu.sg"   # fictional seeded account
DEMO_PASSWORD = "OccuscopeDemo26!"                  # shared demo password from BOOKING_SETUP.md


def call(url, method="GET", body=None, headers=None, timeout=30):
    """Return (status, seconds, body_text, headers)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "content-type": "application/json", "x-occuscope-request": "1", **(headers or {})})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, time.perf_counter() - start, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, time.perf_counter() - start, e.read().decode(errors="replace"), e.headers
    except Exception as e:  # timeouts, connection resets
        return 0, time.perf_counter() - start, repr(e), {}


def pct(values, p):
    if not values:
        return None
    values = sorted(values)
    return round(values[min(len(values) - 1, int(len(values) * p))] * 1000)


def run_phase(name, url, workers, seconds):
    results, lock, stop = [], threading.Lock(), time.time() + seconds

    def worker():
        while time.time() < stop:
            status, secs, _, _ = call(url)
            with lock:
                results.append((status, secs))

    began = time.time()
    with ThreadPoolExecutor(workers) as pool:
        for _ in range(workers):
            pool.submit(worker)
    elapsed = time.time() - began
    ok = [s for st, s in results if st == 200]
    return {
        "phase": name, "workers": workers, "duration_s": round(elapsed, 1),
        "requests": len(results), "req_per_s": round(len(results) / elapsed, 1),
        "status_counts": dict(sorted(Counter(st for st, _ in results).items())),
        "server_errors_5xx": sum(1 for st, _ in results if st >= 500 or st == 0),
        "latency_ms_200": {"p50": pct(ok, .50), "p95": pct(ok, .95), "p99": pct(ok, .99),
                           "max": round(max(ok) * 1000) if ok else None,
                           "mean": round(statistics.mean(ok) * 1000) if ok else None},
    }


def run_auth_burst(base, n=30):
    statuses = [call(f"{base}/api/auth/me")[0] for _ in range(n)]
    return {"phase": "C auth throttle", "requests": n, "status_counts": dict(sorted(Counter(statuses).items()))}


def call_retry(log, label, url, method="GET", body=None, headers=None, attempts=5):
    """Retry while the single-writer Lambda is busy (API Gateway answers 503/429).

    crowdmap-bookings has reserved concurrency 1, so a request that arrives while
    another one (e.g. an open browser tab) is running is throttled, not queued.
    A throttled request never reached the app, so retrying a POST is safe.
    """
    for attempt in range(1, attempts + 1):
        st, secs, text, hdr = call(url, method, body, headers)
        log(f"{label} attempt {attempt} -> {st}")
        if st not in (0, 429, 503):
            break
        time.sleep(3 * attempt)
    return st, secs, text, hdr


def run_persistence(base, function="crowdmap-bookings"):
    out = {"phase": "D persistence across cold start", "steps": []}
    log = out["steps"].append
    for attempt in range(1, 6):  # the auth route is throttled to 2 req/s, so back off on 429
        st, _, body, hdr = call(f"{base}/api/auth/login", "POST", {"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        log(f"login attempt {attempt} -> {st}")
        if st != 429:
            break
        time.sleep(5 * attempt)
    if st != 200:
        out["result"] = "FAIL (login)"
        return out
    cookie = hdr.get("Set-Cookie", "").split(";")[0]
    auth = {"Cookie": cookie}
    day = (datetime.now(SGT) + timedelta(days=3)).date().isoformat()
    room = "E2-04-20-DR223"
    _, _, body, _ = call(f"{base}/api/bookings/availability?location_id={room}&date={day}", headers=auth)
    free = [s["start_time"] for s in json.loads(body).get("slots", []) if s.get("available")]
    if not free:
        out["result"] = "SKIPPED (no free slot)"
        return out
    st, _, body, _ = call_retry(log, f"book {room} {free[-1]}", f"{base}/api/bookings", "POST",
                                {"location_id": room, "slots": [free[-1]]}, auth)
    if st not in (200, 201):
        out["result"] = f"FAIL (booking {st}: {body[:120]})"
        return out
    booking_id = json.loads(body)["bookings"][0]["booking_id"]
    # Changing the description forces Lambda to start fresh instances (cold start).
    subprocess.run(["aws", "lambda", "update-function-configuration", "--function-name", function,
                    "--description", f"resilience test restart {int(time.time())}"],
                   check=True, capture_output=True)
    subprocess.run(["aws", "lambda", "wait", "function-updated", "--function-name", function], check=True)
    log(f"forced cold start of {function}")
    st, secs, body, _ = call_retry(log, "my bookings after restart", f"{base}/api/bookings/mine", headers=auth)
    survived = booking_id in body
    log(f"after restart: my bookings -> {st} in {round(secs * 1000)} ms, booking present = {survived}")
    call_retry(log, "cleanup: cancel", f"{base}/api/bookings/{booking_id}/cancel", "POST", {}, auth)
    out["result"] = "PASS" if survived else "FAIL (booking lost)"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base", help="API Gateway invoke URL, no trailing slash")
    ap.add_argument("--persistence", action="store_true", help="also run phase D (needs AWS CLI)")
    ap.add_argument("--only-persistence", action="store_true", help="run only phase D (after a pause)")
    ap.add_argument("--only-steady", action="store_true", help="run only phase A (for before/after comparisons)")
    ap.add_argument("--out", default="resilience-run.txt")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    at = "2026-10-08T12:00:00%2B08:00"

    started = datetime.now(SGT).strftime("%Y-%m-%d %H:%M SGT")
    call(f"{base}/api/health")  # warm up
    if a.only_persistence:
        report = {"run_started": started, "target": "<API_URL>", "phases": [run_persistence(base)]}
    elif a.only_steady:
        report = {"run_started": started, "target": "<API_URL>", "phases": [
            run_phase("A steady load", f"{base}/api/occupancy/current?at={at}", workers=10, seconds=60)]}
    else:
        report = {"run_started": started, "target": "<API_URL>", "phases": [
            run_phase("A steady load", f"{base}/api/occupancy/current?at={at}", workers=10, seconds=60),
            run_phase("B spike above stage limit", f"{base}/api/locations", workers=60, seconds=15),
            run_auth_burst(base),
        ]}
        if a.persistence:
            time.sleep(30)  # let the auth route's throttle bucket refill after phase C
            report["phases"].append(run_persistence(base))
    text = json.dumps(report, indent=2).replace(base, "<API_URL>")
    print(text)
    with open(a.out, "w") as f:
        f.write(text + "\n")
    print(f"\nSaved to {a.out}")


if __name__ == "__main__":
    main()
