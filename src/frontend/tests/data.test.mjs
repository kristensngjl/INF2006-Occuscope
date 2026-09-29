import test from 'node:test';
import assert from 'node:assert/strict';
import {parseCSV,band,currentRows,dayEvents} from '../data.js';
test('CSV supports quoted commas, escaped quotes and CRLF',()=>assert.deepEqual(parseCSV('id,name\r\n1,"Room, ""A"""\r\n'),[{id:'1',name:'Room, "A"'}]));
test('crowd boundaries and missing data remain distinct',()=>assert.deepEqual([null,0,.3,.3001,.7,.71].map(band),['unknown','quiet','quiet','moderate','moderate','crowded']));
test('current readings never use a future seed row; missing stays unknown',()=>{const locations=[{location_id:'a',capacity:10},{location_id:'b',capacity:8}];const readings=[{location_id:'a',timestamp:'2026-09-29T16:00:00+08:00',occupancy_count:9},{location_id:'a',timestamp:'2026-09-29T14:00:00+08:00',occupancy_count:3}];const rows=currentRows(locations,readings,'2026-09-29T15:00:00+08:00');assert.equal(rows[0].occupancy_count,3);assert.equal(rows[0].crowd_level,'quiet');assert.equal(rows[1].occupancy_count,null);assert.equal(rows[1].crowd_level,'unknown');});
test('multi-day events overlap the selected Singapore day',()=>{const e={start_time:'2026-09-28T10:00:00+08:00',end_time:'2026-10-04T18:00:00+08:00'};assert.equal(dayEvents([e],'2026-09-29').length,1);assert.equal(dayEvents([e],'2026-10-05').length,0);});
