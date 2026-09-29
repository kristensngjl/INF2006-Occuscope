export function parseCSV(text) {
  const rows=[]; let row=[], value='', quoted=false;
  for(let i=0;i<text.length;i++) {
    const c=text[i];
    if(c==='"') {if(quoted && text[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}
    else if(c===',' && !quoted){row.push(value);value='';}
    else if(c==='\n' && !quoted){row.push(value.replace(/\r$/,''));rows.push(row);row=[];value='';}
    else value+=c;
  }
  if(value || row.length){row.push(value.replace(/\r$/,''));rows.push(row);}
  const headers=rows.shift() || [];
  return rows.filter(r=>r.some(Boolean)).map(r=>Object.fromEntries(headers.map((h,i)=>[h.replace(/^\uFEFF/,''),r[i]??''])));
}
export const band = ratio => ratio == null ? 'unknown' : ratio <= .3 ? 'quiet' : ratio <= .7 ? 'moderate' : 'crowded';
export function currentRows(locations, readings, at) {
  const latest=new Map(); const target=Date.parse(at);
  for(const r of readings){const time=Date.parse(r.timestamp);if(time<=target && (!latest.has(r.location_id)||time>Date.parse(latest.get(r.location_id).timestamp)))latest.set(r.location_id,r);}
  return locations.map(l=>{const r=latest.get(l.location_id);const count=r ? Number(r.occupancy_count):null;const ratio=count===null?null:count/Number(l.capacity);return {...l,...r,occupancy_count:count,occupancy_ratio:ratio,crowd_level:band(ratio)};});
}
export function dayEvents(events,date) {return events.filter(e=>Date.parse(e.start_time)<Date.parse(`${date}T23:59:59+08:00`)&&Date.parse(e.end_time)>Date.parse(`${date}T00:00:00+08:00`));}
async function get(url){const r=await fetch(url,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw new Error(`Data request failed (${r.status}). Check that ${url.startsWith('/api')?'the backend is running on port 8000':'the sample files are available'}.`);return r;}
export async function sampleData(){const names=['buildings','locations','events','occupancy_generated','occupancy_prediction'];const values=await Promise.all(names.map(async n=>parseCSV(await (await get(`/sample/${n}.csv`)).text())));return Object.fromEntries(names.map((n,i)=>[n,values[i]]));}
export async function api(endpoint,params={}) {return (await get(`/api/${endpoint}?${new URLSearchParams(params)}`)).json();}
