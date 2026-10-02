# Demo student accounts and discussion-room booking

Accounts are pre-created by `python -m src.db.seed_students`: 1,998 fictional profiles for 2500001–2500999 and 2600001–2600999, with generated names and `studentid@sit.singaporetech.edu.sg` addresses. Shared demo password: `OccuscopeDemo26!`. Login requires the full email and password. Self-registration is disabled. No real student IDs are verified, and no emails are sent. The login screen offers a password visibility toggle.

Restart both the API and Node frontend server after pulling this change. The API must have write access to the same SQLite database it serves for locations. The first account/booking request applies `booking_schema.sql` additively: it preserves the existing location, occupancy, event, and app_user tables. No destructive database rebuild is needed to enable booking. If you run `init_app_db.py`, it wipes the database then re-seeds campus rows, demo accounts, and discussion-room demo bookings; stop/restart the backend around a rebuild.

Select a discussion room on the map or list, click **Book discussion room**, sign in, and choose a date and one or more available 30-minute blocks. Other location types have no booking button and are rejected by the API as well. **My bookings** lists only the current student's reservations and permits cancellation before the start time.

Project rules (not official SIT policy): 08:00–20:00 SGT, 30-minute increments, 240 minutes per student per Monday–Sunday Singapore-time week, today through 14 days ahead. Only future slots may be reserved. Bookings use actual SGT time, not the occupancy demo picker. Confirmed reservations, overlapping seeded events, and the student's other simultaneous bookings block a new reservation. SQLite `BEGIN IMMEDIATE` makes conflict checking and insertion atomic. Cancelled bookings release the slot and restore its minutes to that week. Non-consecutive blocks are supported; the selected batch is committed atomically. All confirmed bookings in the week, including past ones, count toward the limit. Availability returns the signed-in student’s weekly used and remaining minutes, and excludes their overlapping reservations in other rooms. Occupancy and AI forecasts never determine reservation availability. The chatbot cannot create bookings or access account information.

Passwords use salted PBKDF2-SHA256 (600,000 iterations). Random eight-hour sessions are stored hashed in the database and carried in HttpOnly, SameSite=Strict cookies. Mutation requests require a custom header; the frontend proxy also rejects cross-origin mutations. No credentials are stored in browser localStorage. Login/registration are limited to ten attempts per minute per backend-visible client address. With the Node proxy this is a shared limit, suitable for a small local demo; a public deployment needs shared gateway rate limiting. No password recovery is implemented for these fictional accounts.

For an HTTPS AWS deployment set `COOKIE_SECURE=1` on the API and `PUBLIC_ORIGIN=https://your-site-host` on the Node proxy. Keep API access behind the same-origin frontend/gateway, preserve Cookie and Set-Cookie headers, and use persistent database storage. This implementation supports SQLite on one host; do not deploy independent SQLite copies across Lambda/EC2 instances. A shared relational database migration is needed before horizontally scaling bookings. Login accepts only the two seeded ID ranges at `sit.singaporetech.edu.sg`; this is format validation, not SIT identity verification.

Run offline tests (temporary databases; no real accounts or paid APIs):

```powershell
python -m unittest src.backend.test_bookings src.backend.test_chat
```

Routes: POST `/auth/login`, `/auth/logout`; GET `/auth/me`, `/bookings/mine`, `/bookings/availability?location_id=...&date=YYYY-MM-DD`; POST `/bookings`, `/bookings/{booking_id}/cancel`. Frontend routes add the `/api` prefix. Availability returns anonymous half-hour slots, never other students' details.

Booking requests use `{ "location_id": "...", "slots": ["2026-10-03T09:00:00+08:00"] }` (one to eight half-hour start times). The response contains `bookings` and `booked_minutes`. The old start/end request format and registration endpoint have been removed.
