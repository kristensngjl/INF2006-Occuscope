import io
import json
import os
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from . import chat

class ChatTests(unittest.TestCase):
 def setUp(self):
  chat._calls.clear()
 def test_no_key(self):
  with patch.dict(os.environ, {"GROQ_API_KEY": ""}), patch.object(chat.Path, "read_text", side_effect=FileNotFoundError):
   with self.assertRaises(HTTPException) as error: chat.answer("Hi", "time", [])
   self.assertEqual(error.exception.status_code,503)
 def test_validated_room_ids(self):
  response={"choices":[{"message":{"content":json.dumps({"answer":"Try A", "location_ids":["a","invented","a"]})}}]}
  with patch.dict(os.environ,{"GROQ_API_KEY":"test-only"}), patch.object(chat,"urlopen",return_value=io.BytesIO(json.dumps(response).encode())) as provider:
   result=chat.answer("Find a room","2026-09-30T15:00:00+08:00",[{"location_id":"a"}])
   self.assertEqual(result["location_ids"],["a"])
   payload=json.loads(provider.call_args.args[0].data)
   self.assertIn('ROOM SNAPSHOT',payload['messages'][0]['content'])
 def test_invalid_response(self):
  with patch.dict(os.environ,{"GROQ_API_KEY":"test-only"}), patch.object(chat,"urlopen",return_value=io.BytesIO(b'{}')):
   with self.assertRaises(HTTPException) as error: chat.answer("Hi","time",[])
   self.assertEqual(error.exception.status_code,502)

 def test_forecast_context(self):
  response={"choices":[{"message":{"content":json.dumps({"answer":"Generated estimate", "location_ids":["a"]})}}]}
  forecasts=[{"location_id":"a","predicted_for":"2026-10-02T16:00:00+08:00","occupancy_count":2}]
  with patch.dict(os.environ,{"GROQ_API_KEY":"test-only"}), patch.object(chat,"urlopen",return_value=io.BytesIO(json.dumps(response).encode())) as provider:
   chat.answer("Quieter in an hour?","2026-10-02T15:00:00+08:00",[{"location_id":"a","capacity":10,"type":"discussion_room"}],forecasts)
   prompt=json.loads(provider.call_args.args[0].data)["messages"][0]["content"]
   future=json.loads(prompt.split("NEXT TWO HOURS FORECAST (generated v0): ")[1])
   self.assertEqual(future["rows"],[["a","2026-10-02T16:00:00+08:00",2]])
   self.assertIn("Missing forecast rows mean unavailable",prompt)
   self.assertIn("discussion_room",prompt)

class ForecastRouteTests(unittest.TestCase):
 def setUp(self):
  import csv
  import sqlite3
  import tempfile
  from pathlib import Path
  from .api import create_app
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  db=Path(self.temp.name)/"test.db"
  root=Path(__file__).resolve().parents[2]
  with sqlite3.connect(db) as conn:
   conn.executescript((root/"src/db/schema.sql").read_text(encoding="utf-8"))
   for table,filename in [("building","buildings.csv"),("location","locations.csv")]:
    with (root/"data/sample"/filename).open(encoding="utf-8",newline="") as f:
     reader=csv.DictReader(f)
     columns=reader.fieldnames
     conn.executemany(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",[tuple(row[c] for c in columns) for row in reader])
   self.ids=[r[0] for r in conn.execute("SELECT location_id FROM location ORDER BY location_id")]
   for day in ["2026-09-30","2026-10-02"]:
    for hour in [15,16,17,18,20]:
     conn.executemany("INSERT INTO occupancy(location_id,timestamp,occupancy_count) VALUES (?,?,?)",[(i,f"{day}T{hour}:00:00+08:00",hour-15) for i in self.ids])
   conn.execute("INSERT INTO occupancy(location_id,timestamp,occupancy_count) VALUES (?,?,?)",(self.ids[0],"2026-10-03T08:00:00+08:00",1))
  conn.close()
  self.endpoint=next(r.endpoint for r in create_app(db).routes if r.path=="/chat")
 def test_selected_date_and_all_catalogue_rooms(self):
  for day in ["2026-09-30","2026-10-02"]:
   instant=f"{day}T15:00:00+08:00"
   with self.subTest(day=day), patch("src.backend.api.answer",return_value={}) as answer:
    self.endpoint(chat.ChatInput(message="Next two hours?",at=instant))
    _,at,rooms,forecasts=answer.call_args.args
    self.assertEqual(at,instant)
    self.assertEqual({r["location_id"] for r in rooms},set(self.ids))
    self.assertEqual(len(forecasts),2*len(self.ids))
    self.assertEqual({r["predicted_for"] for r in forecasts},{f"{day}T16:00:00+08:00",f"{day}T17:00:00+08:00"})
 def test_no_next_day_substitution(self):
  with patch("src.backend.api.answer",return_value={}) as answer:
   self.endpoint(chat.ChatInput(message="Next two hours?",at="2026-10-02T20:00:00+08:00"))
   self.assertEqual(answer.call_args.args[3],[])
 def test_partial_forecast_keeps_missing_hour_missing(self):
  with patch("src.backend.api.answer",return_value={}) as answer:
   self.endpoint(chat.ChatInput(message="Next two hours?",at="2026-10-02T18:00:00+08:00"))
   forecasts=answer.call_args.args[3]
   self.assertEqual(len(forecasts),len(self.ids))
   self.assertEqual({r["predicted_for"] for r in forecasts},{"2026-10-02T20:00:00+08:00"})
