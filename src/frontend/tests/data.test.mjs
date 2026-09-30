import test from 'node:test';
import assert from 'node:assert/strict';
import {band,dayEvents} from '../data.js';
test('crowd boundaries and missing data remain distinct',()=>assert.deepEqual([null,0,.3,.3001,.7,.71].map(band),['unknown','quiet','quiet','moderate','moderate','crowded']));
test('multi-day events overlap the selected Singapore day',()=>{const e={start_time:'2026-09-28T10:00:00+08:00',end_time:'2026-10-04T18:00:00+08:00'};assert.equal(dayEvents([e],'2026-09-29').length,1);assert.equal(dayEvents([e],'2026-10-05').length,0);});
