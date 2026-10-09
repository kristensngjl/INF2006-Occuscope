"""Atomic grouped cancellation against a disposable SQLite database."""
from contextlib import closing
import hashlib
import sqlite3
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import HTTPException, Request
from .bookings import create_router, CancelBookingsInput, SGT

class GroupCancellationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.db=Path(self.temp.name)/'test.db'
  with closing(sqlite3.connect(self.db)) as c, c:
   c.executescript("CREATE TABLE app_user(user_id TEXT PRIMARY KEY,email TEXT,role TEXT); CREATE TABLE location(location_id TEXT PRIMARY KEY);")
   c.executescript(Path(__file__).with_name('booking_schema.sql').read_text())
   c.execute("INSERT INTO app_user VALUES ('u','test@example.com','student')")
   c.execute("INSERT INTO app_user VALUES ('other','other@example.com','student')")
   c.execute("INSERT INTO student_profile VALUES ('u','2500001','Test Student',1)")
   c.execute("INSERT INTO student_session VALUES (?,?,?)",(hashlib.sha256(b'test-token').hexdigest(),'u',int(time.time())+3600))
   c.execute("INSERT INTO location VALUES ('room')")
   future=datetime.now(SGT)+timedelta(days=1)
   for bid,uid,start in [('a','u',future),('b','u',future+timedelta(minutes=30)),('foreign','other',future),('past','u',future-timedelta(days=2))]:
    c.execute("INSERT INTO room_booking VALUES (?,?,?,?,?,'confirmed',?)",(bid,uid,'room',start.isoformat(),(start+timedelta(minutes=30)).isoformat(),future.isoformat()))
  router=create_router(self.db,None)
  self.cancel=next(r.endpoint for r in router.routes if r.path=='/bookings/cancel')
  self.request=Request({'type':'http','headers':[(b'cookie',b'occuscope_session=test-token'),(b'x-occuscope-request',b'1')]})
 def states(self):
  with closing(sqlite3.connect(self.db)) as c, c:return dict(c.execute('SELECT booking_id,status FROM room_booking'))
 def test_all_slots_cancel_and_retry_is_safe(self):
  for _ in range(2):self.assertEqual(self.cancel(CancelBookingsInput(booking_ids=['a','b']),self.request),{'ok':True})
  self.assertEqual(self.states()['a'],'cancelled');self.assertEqual(self.states()['b'],'cancelled')
 def test_foreign_missing_and_past_ids_cannot_partially_cancel(self):
  for bad,code in [('foreign',404),('missing',404),('past',409)]:
   with self.assertRaises(HTTPException) as error:self.cancel(CancelBookingsInput(booking_ids=['a',bad]),self.request)
   self.assertEqual(error.exception.status_code,code);self.assertEqual(self.states()['a'],'confirmed')
 def test_guard_and_session_required(self):
  for headers,code in [([],403),([(b'x-occuscope-request',b'1')],401)]:
   with self.assertRaises(HTTPException) as error:self.cancel(CancelBookingsInput(booking_ids=['a']),Request({'type':'http','headers':headers}))
   self.assertEqual(error.exception.status_code,code)
