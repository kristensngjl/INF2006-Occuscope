"""Add 1,998 fictional trial students without replacing campus data or existing accounts.

Run from the repository root: python -m src.db.seed_students
"""
import argparse
import os
import random
import sqlite3
from contextlib import closing
from pathlib import Path

from src.backend.bookings import password_hash

ROOT = Path(__file__).resolve().parents[2]
DOMAIN = "sit.singaporetech.edu.sg"
# Intentionally public password for fictional project accounts only.
DEMO_PASSWORD = "OccuscopeDemo26!"


def trial_students():
    first = ["Avery", "Jamie", "Riley", "Morgan", "Casey", "Jordan", "Taylor", "Alex", "Robin", "Skyler",
             "Nadia", "Amir", "Zara", "Danish", "Hana", "Kiran", "Priya", "Arjun", "Anika", "Dev",
             "Chloe", "Ethan", "Olivia", "Noah", "Isabel", "Lucas", "Maya", "Ryan", "Sofia", "Adam",
             "Leah", "Aaron", "Grace", "Isaac", "Clara", "Daniel", "Sarah", "Nathan", "Emma", "Evan"]
    last = ["Tan", "Lim", "Teo", "Ng", "Goh", "Lee", "Wong", "Koh", "Chen", "Ong",
            "Rahman", "Hassan", "Abdullah", "Ismail", "Yusuf", "Nair", "Rao", "Menon", "Shah", "Raman",
            "Chan", "Chua", "Low", "Yeo", "Lau", "Tay", "Ho", "Sim", "Chong", "Foo",
            "Neo", "Toh", "Wee", "Seah", "Chin", "Yap", "Liew", "Ang", "Loh", "Chew",
            "Gan", "Pillai", "Kumar", "Singh", "Ali", "Ibrahim", "Aziz", "Das", "Sen", "Soh"]
    names = [f"{given} {family}" for given in first for family in last]
    random.Random(2006).shuffle(names)
    ids = [f"{prefix}{number:03d}" for prefix in ("2500", "2600") for number in range(1,1000)]
    return [{"student_id": sid, "email": f"{sid}@{DOMAIN}", "display_name": name}
            for sid, name in zip(ids, names)]


def seed_students(path, students=None):
    path = Path(path).resolve()
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript((ROOT / "src/backend/booking_schema.sql").read_text(encoding="utf-8"))
        inserted = 0
        demo_hash = password_hash(DEMO_PASSWORD)
        with conn:
            for row in (trial_students() if students is None else students):
                user_id = "trial-" + row["student_id"]
                existing = conn.execute("""SELECT u.user_id,u.email,p.student_id,p.display_name
                    FROM app_user u LEFT JOIN student_profile p ON p.user_id=u.user_id
                    WHERE u.user_id=? OR u.email=?""", (user_id,row["email"])).fetchall()
                if existing:
                    if len(existing) != 1 or existing[0][:3] != (user_id,row["email"],row["student_id"]):
                        raise ValueError(f"Existing account conflicts with trial student {row['student_id']}; no accounts overwritten.")
                    continue
                conn.execute("INSERT INTO app_user(user_id,email,role) VALUES (?,?,'student')", (user_id,row["email"]))
                conn.execute("INSERT INTO student_profile VALUES (?,?,?,1)", (user_id,row["student_id"],row["display_name"]))
                conn.execute("INSERT INTO student_credential VALUES (?,?)", (user_id,demo_hash))
                inserted += 1
        return inserted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, help="Optional SQLite file; otherwise use DATABASE_URL or data/occuscope.db")
    args = parser.parse_args()
    path = args.database
    if path is None:
        url = os.getenv("DATABASE_URL", "sqlite:///data/occuscope.db")
        if not url.startswith("sqlite:///"):
            parser.error("The trial seed currently supports SQLite only.")
        path = Path(url.removeprefix("sqlite:///"))
        if not path.is_absolute():
            path = ROOT / path
    if not path.is_file():
        parser.error("The campus database does not exist. Initialise it first; this script never creates an empty campus database.")
    count = seed_students(path)
    print(f"Added {count} fictional students. Existing accounts and campus data preserved.")
    print("Student IDs: 2500001–2500999 and 2600001–2600999")
    print(f"Trial password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
