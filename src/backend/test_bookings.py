"""Offline HTTP tests using a disposable database and fictional accounts."""
import csv
import http.cookiejar
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor

from .bookings import SGT
from src.db.seed_students import seed_students, trial_students, DEMO_PASSWORD

ROOT = Path(__file__).resolve().parents[2]


class BookingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory()
  cls.db=Path(cls.temp.name)/'bookings.db'
  with sqlite3.connect(cls.db) as conn:
   conn.executescript((ROOT/'src/db/schema.sql').read_text(encoding='utf-8'))
   for table,file in [('building','buildings.csv'),('location','locations.csv')]:
    with (ROOT/'data/sample'/file).open(encoding='utf-8',newline='') as f:
     reader=csv.DictReader(f); columns=reader.fieldnames
     conn.executemany(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",[tuple(row[k] for k in columns) for row in reader])
   cls.rooms=[r[0] for r in conn.execute("SELECT location_id FROM location WHERE type='discussion_room'")]
   cls.study=conn.execute("SELECT location_id FROM location WHERE type!='discussion_room'").fetchone()[0]
   cls.count=conn.execute('SELECT COUNT(*) FROM location').fetchone()[0]
  conn.close()
  seed_students(cls.db, students=trial_students()[:2])
  with socket.socket() as sock:
   sock.bind(('127.0.0.1',0));cls.port=sock.getsockname()[1]
  cls.base=f'http://127.0.0.1:{cls.port}'
  env={**os.environ,'DATABASE_URL':'sqlite:///'+str(cls.db),'COOKIE_SECURE':'0'}
  cls.proc=subprocess.Popen([sys.executable,'-B','-m','uvicorn','src.backend.api:app','--port',str(cls.port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(100):
   try:
    with build_opener().open(cls.base+'/locations',timeout=1): break
   except OSError: time.sleep(.1)
  else:
   cls.proc.terminate();cls.proc.wait();cls.temp.cleanup();raise RuntimeError('Test API failed to start')
  cls.clients=[]
  for i in range(2):
   opener=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
   req=Request(cls.base+'/auth/login',data=json.dumps({'email':f'250000{i+1}@sit.singaporetech.edu.sg','password':DEMO_PASSWORD}).encode(),headers={'Content-Type':'application/json','X-Occuscope-Request':'1'})
   with opener.open(req) as response:
    assert response.status==200
   cls.clients.append(opener)

 @classmethod
 def tearDownClass(cls):
  cls.proc.terminate();cls.proc.wait(timeout=10);cls.temp.cleanup()

 def setUp(self):
  with sqlite3.connect(self.db) as conn:
   conn.execute('DELETE FROM room_booking');conn.execute('DELETE FROM event')
  conn.close()
  self.date=(datetime.now(SGT)+timedelta(days=1)).date().isoformat()

 def call(self,path,body=None,client=0,guard=True):
  opener=self.clients[client] if isinstance(client,int) else client
  headers={'Content-Type':'application/json'}
  if guard: headers['X-Occuscope-Request']='1'
  req=Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
  try:
   with opener.open(req) as r: return r.status,json.load(r),r.headers
  except HTTPError as e: return e.code,json.load(e),e.headers

 def body(self,room=None,start='10:00',end='11:00'):
  first=datetime.fromisoformat(f'{self.date}T{start}:00+08:00')
  last=datetime.fromisoformat(f'{self.date}T{end}:00+08:00')
  return {'location_id':room or self.rooms[0],'slots':[(first+timedelta(minutes=i)).isoformat() for i in range(0,int((last-first).total_seconds()/60),30)]}

 def test_account_storage_and_migration(self):
  status,user,_=self.call('/auth/me');self.assertEqual(status,200);self.assertEqual(user['email'],'2500001@sit.singaporetech.edu.sg')
  with sqlite3.connect(self.db) as conn:
   self.assertEqual(conn.execute('SELECT COUNT(*) FROM location').fetchone()[0],self.count)
   encoded=conn.execute('SELECT password_hash FROM student_credential LIMIT 1').fetchone()[0]
   self.assertNotIn('fictional-password',encoded)
   self.assertTrue(encoded.startswith('pbkdf2_sha256$'))
   self.assertEqual(len(conn.execute('SELECT token_hash FROM student_session LIMIT 1').fetchone()[0]),64)
  conn.close()

 def test_authentication_and_csrf_required(self):
  self.assertEqual(self.call('/bookings',self.body(),client=build_opener())[0],401)
  self.assertEqual(self.call('/bookings',self.body(),guard=False)[0],403)
  self.assertEqual(self.call('/bookings/mine',client=build_opener())[0],401)

 def test_study_space_is_never_bookable(self):
  self.assertEqual(self.call('/bookings',self.body(room=self.study))[0],422)
  self.assertEqual(self.call(f'/bookings/availability?location_id={self.study}&date={self.date}')[0],422)

 def test_booking_privacy_cancellation_and_release(self):
  status,booking,_=self.call('/bookings',self.body(end='10:30'));self.assertEqual(status,201)
  self.assertEqual(len(self.call('/bookings/mine')[1]),1)
  self.assertEqual(self.call('/bookings/mine',client=1)[1],[])
  self.assertEqual(self.call('/bookings/'+booking['bookings'][0]['booking_id']+'/cancel',{},client=1)[0],404)
  self.assertEqual(self.call('/bookings',self.body(),client=1)[0],409)
  self.assertEqual(self.call('/bookings/'+booking['bookings'][0]['booking_id']+'/cancel',{})[0],200)
  self.assertEqual(self.call('/bookings',self.body(),client=1)[0],201)

 def test_concurrent_booking_only_one_wins(self):
  with ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(lambda i:self.call('/bookings',self.body(),client=i)[0],[0,1]))
  self.assertEqual(sorted(results),[201,409])

 def test_own_overlap_and_adjacent_slots(self):
  self.assertEqual(self.call('/bookings',self.body())[0],201)
  self.assertEqual(self.call('/bookings',self.body(room=self.rooms[1]))[0],409)
  self.assertEqual(self.call('/bookings',self.body(start='11:00',end='11:30'))[0],201)

 def test_events_and_availability(self):
  body=self.body()
  with sqlite3.connect(self.db) as conn:
   conn.execute('INSERT INTO event(event_id,location_id,title,start_time,end_time) VALUES (?,?,?,?,?)',('test-event',self.rooms[0],'Demo event',body['slots'][0],f'{self.date}T11:00:00+08:00'))
  conn.close()
  self.assertEqual(self.call('/bookings',body)[0],409)
  status,result,_=self.call(f'/bookings/availability?location_id={self.rooms[0]}&date={self.date}')
  self.assertEqual(status,200)
  blocked=[s for s in result['slots'] if not s['available']]
  self.assertEqual(len(blocked),2)
  self.assertNotIn('email',json.dumps(result))

 def test_invalid_times(self):
  for start,end in [('07:30','08:00'),('19:30','20:30'),('10:15','11:15'),('10:00','14:30'),('11:00','10:00')]:
   self.assertEqual(self.call('/bookings',self.body(start=start,end=end))[0],422)
  body=self.body();body['slots']=['2020-01-01T10:00:00+08:00']
  self.assertEqual(self.call('/bookings',body)[0],422)
  body=self.body();body['slots'][0]=body['slots'][0].replace('+08:00','Z')
  self.assertEqual(self.call('/bookings',body)[0],422)

 def test_login_logout_cookie_and_bad_password(self):
  client=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
  credentials={'email':'2500001@sit.singaporetech.edu.sg','password':'incorrect-password'}
  self.assertEqual(self.call('/auth/login',credentials,client=client)[0],401)
  credentials['password']=DEMO_PASSWORD
  status,_,headers=self.call('/auth/login',credentials,client=client)
  self.assertEqual(status,200);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=strict',headers['Set-Cookie'])
  self.assertEqual(self.call('/auth/me',client=client)[0],200)
  self.assertEqual(self.call('/auth/logout',{},client=client)[0],200)
  self.assertEqual(self.call('/auth/me',client=client)[0],401)

 def test_exact_student_ranges_and_email_only(self):
  for email in ['2500000@sit.singaporetech.edu.sg','2600000@sit.singaporetech.edu.sg','2501000@sit.singaporetech.edu.sg','2601000@sit.singaporetech.edu.sg','2500001','2500001@example.test']:
   # Call a fresh router directly so this validation test does not exhaust the HTTP login throttle.
   from .bookings import create_router, Credentials
   from .api import parse_time
   from starlette.requests import Request as StarletteRequest
   from starlette.responses import Response
   from fastapi import HTTPException
   endpoint=next(r.endpoint for r in create_router(self.db,parse_time).routes if r.path=='/auth/login')
   request=StarletteRequest({'type':'http','headers':[(b'x-occuscope-request',b'1')],'client':('test',1)})
   with self.subTest(email=email), self.assertRaises(HTTPException) as error:
    endpoint(Credentials(email=email,password=DEMO_PASSWORD),request,Response())
   self.assertEqual(error.exception.status_code,422)

 def test_registration_disabled(self):
  self.assertEqual(self.call('/auth/register',{'email':'2500999@sit.singaporetech.edu.sg','password':DEMO_PASSWORD})[0],404)

 def test_weekly_allowance_and_cancel_refund(self):
  blocks=[f'{self.date}T{hour:02d}:{minute}:00+08:00' for hour in range(8,12) for minute in ('00','30')]
  status,result,_=self.call('/bookings',{'location_id':self.rooms[0],'slots':blocks})
  self.assertEqual(status,201);self.assertEqual(result['booked_minutes'],240)
  self.assertEqual(self.call('/bookings',self.body(start='12:00',end='12:30'))[0],409)
  self.assertEqual(self.call('/bookings/'+result['bookings'][0]['booking_id']+'/cancel',{})[0],200)
  self.assertEqual(self.call('/bookings',self.body(start='12:00',end='12:30'))[0],201)

 def test_batch_conflict_is_atomic_and_duplicates_rejected(self):
  self.assertEqual(self.call('/bookings',self.body(),client=1)[0],201)
  blocks=[f'{self.date}T09:00:00+08:00',f'{self.date}T10:00:00+08:00']
  self.assertEqual(self.call('/bookings',{'location_id':self.rooms[0],'slots':blocks})[0],409)
  self.assertEqual(self.call('/bookings/mine')[1],[])
  self.assertEqual(self.call('/bookings',{'location_id':self.rooms[0],'slots':[blocks[0],blocks[0]]})[0],422)

 def test_nonconsecutive_blocks_and_separate_weeks(self):
  status,result,_=self.call('/bookings',{'location_id':self.rooms[0],'slots':[f'{self.date}T09:00:00+08:00',f'{self.date}T11:30:00+08:00']})
  self.assertEqual(status,201);self.assertEqual(result['booked_minutes'],60)
  weekly=self.call(f'/bookings/availability?location_id={self.rooms[0]}&date={self.date}')[1]['weekly_allowance']
  self.assertEqual(weekly['remaining_minutes'],180)
  other=(datetime.fromisoformat(weekly['week_start'])+timedelta(days=7)).date().isoformat()
  if other<=self.date: other=(datetime.fromisoformat(other)+timedelta(days=7)).date().isoformat()
  weekly_other=self.call(f'/bookings/availability?location_id={self.rooms[0]}&date={other}')[1]['weekly_allowance']
  self.assertEqual(weekly_other['remaining_minutes'],240)

 def test_concurrent_requests_cannot_exceed_weekly_quota(self):
  self.assertEqual(self.call('/bookings',self.body(start='08:00',end='11:30'))[0],201)
  # Two distinct free blocks compete for the same student's final 30 minutes.
  with ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(lambda hour:self.call('/bookings',self.body(start=f'{hour}:00',end=f'{hour}:30'))[0],['12','13']))
  self.assertEqual(sorted(results),[201,409])

class StudentCatalogueTests(unittest.TestCase):
 def test_exact_1998_fictional_students(self):
  rows=trial_students()
  ids={r['student_id'] for r in rows}
  expected={str(n) for n in range(2500001,2501000)}|{str(n) for n in range(2600001,2601000)}
  self.assertEqual(len(rows),1998)
  self.assertEqual(ids,expected)
  self.assertEqual(len({r['display_name'] for r in rows}),1998)
  self.assertTrue(all(r['email']==r['student_id']+'@sit.singaporetech.edu.sg' for r in rows))

 def test_seed_is_idempotent_and_preserves_passwords(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'seed.db'
   with sqlite3.connect(path) as conn:
    conn.executescript((ROOT/'src/db/schema.sql').read_text(encoding='utf-8'))
   conn.close()
   students=[trial_students()[0],trial_students()[998],trial_students()[999],trial_students()[-1]]
   self.assertEqual(seed_students(path,students),4)
   with sqlite3.connect(path) as conn:
    before=conn.execute('SELECT * FROM student_credential ORDER BY user_id').fetchall()
   conn.close()
   self.assertEqual(seed_students(path,students),0)
   with sqlite3.connect(path) as conn:
    self.assertEqual(before,conn.execute('SELECT * FROM student_credential ORDER BY user_id').fetchall())
   conn.close()
