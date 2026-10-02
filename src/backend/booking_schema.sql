-- Additive migration: preserve existing campus data and app_user identities.
CREATE TABLE IF NOT EXISTS student_credential (
 user_id TEXT PRIMARY KEY REFERENCES app_user(user_id), password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS student_profile (
 user_id TEXT PRIMARY KEY REFERENCES app_user(user_id),
 student_id TEXT NOT NULL UNIQUE CHECK(length(student_id)=7 AND ((student_id GLOB '2500[0-9][0-9][0-9]' AND student_id!='2500000') OR (student_id GLOB '2600[0-9][0-9][0-9]' AND student_id!='2600000'))),
 display_name TEXT NOT NULL, is_demo INTEGER NOT NULL DEFAULT 1 CHECK(is_demo=1)
);
CREATE TABLE IF NOT EXISTS student_session (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES app_user(user_id), expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS room_booking (
 booking_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES app_user(user_id),
 location_id TEXT NOT NULL REFERENCES location(location_id), start_time TEXT NOT NULL, end_time TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed','cancelled')),
 created_at TEXT NOT NULL, CHECK(end_time > start_time)
);
CREATE INDEX IF NOT EXISTS idx_booking_room_time ON room_booking(location_id,start_time,end_time);
CREATE INDEX IF NOT EXISTS idx_booking_user ON room_booking(user_id,start_time);
