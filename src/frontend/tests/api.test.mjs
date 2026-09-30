import test from 'node:test';
import assert from 'node:assert/strict';

// Opt in after starting both servers: OCCUSCOPE_INTEGRATION=1 node --test tests/*.test.mjs
test('selected-time frontend proxy returns populated teaching-day occupancy', {skip:process.env.OCCUSCOPE_INTEGRATION!=='1'},async()=>{
 const at='2026-09-30T15:00:00+08:00';
 const origin=process.env.FRONTEND_ORIGIN || 'http://127.0.0.1:5173';
 const response=await fetch(`${origin}/api/occupancy/current?${new URLSearchParams({at})}`);
 assert.equal(response.status,200);
 const rows=await response.json();
 const catalogue=await (await fetch(`${origin}/api/locations`)).json();
 assert.deepEqual(rows.map(r=>r.location_id).sort(),catalogue.map(r=>r.location_id).sort(), 'Occupancy must include all API locations');
 assert.ok(rows.some(r=>r.occupancy_count>0));
 for(const r of rows){
   assert.equal(r.timestamp,at);
   for(const k of ['map_x','map_y','occupancy_ratio','crowd_level'])assert.ok(k in r);
   assert.equal(r.source,'generated');
   assert.ok(Math.abs(r.occupancy_ratio-r.occupancy_count/r.capacity)<0.0001);
   assert.equal(r.crowd_level,r.occupancy_count/r.capacity<=.3?'quiet':r.occupancy_count/r.capacity<=.7?'moderate':'crowded');
 }
 const missingAt=await fetch(`${origin}/api/occupancy/current`);
 assert.equal(missingAt.status,422);
 assert.equal((await fetch(`${origin}/sample/locations.csv`)).status,404);
});
