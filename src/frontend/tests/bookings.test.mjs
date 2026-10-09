import {test} from 'node:test';
import assert from 'node:assert/strict';
import {groupBookings} from '../data.js';
const slot=(id,start,end,location_id='E2',status='confirmed')=>({booking_id:id,location_id,status,start_time:`2026-10-11T${start}:00+08:00`,end_time:`2026-10-11T${end}:00+08:00`});
test('consecutive slots group with every cancellation ID without mutating input',()=>{
 const input=[slot('b','13:30','14:00'),slot('a','13:00','13:30'),slot('c','14:00','14:30')];
 const copy=JSON.stringify(input);const groups=groupBookings(input);
 assert.equal(groups.length,1);assert.deepEqual(groups[0].booking_ids,['a','b','c']);assert.equal(groups[0].end_time,input[2].end_time);assert.equal(JSON.stringify(input),copy);
});
test('gaps, rooms and statuses stay separate',()=>{
 assert.equal(groupBookings([slot('a','13:00','13:30'),slot('b','14:00','14:30'),slot('c','13:30','14:00','W1'),slot('d','13:30','14:00','E2','cancelled')]).length,4);
});
test('different Singapore dates stay separate',()=>{
 const a=slot('a','23:30','23:59');a.end_time='2026-10-12T00:00:00+08:00';
 const b={...slot('b','00:00','00:30'),start_time:a.end_time,end_time:'2026-10-12T00:30:00+08:00'};
 assert.equal(groupBookings([a,b]).length,2);
});
