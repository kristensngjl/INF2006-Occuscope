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
