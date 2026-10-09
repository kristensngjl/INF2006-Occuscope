export const band = ratio => ratio == null ? 'unknown' : ratio <= .3 ? 'quiet' : ratio <= .7 ? 'moderate' : 'crowded';
export function dayEvents(events,date) {return events.filter(e=>Date.parse(e.start_time)<Date.parse(`${date}T23:59:59+08:00`)&&Date.parse(e.end_time)>Date.parse(`${date}T00:00:00+08:00`));}
async function get(url){const r=await fetch(url,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw new Error(`API request failed (${r.status}). Check that the backend is running.`);return r;}
export async function api(endpoint,params={}) {return (await get(`/api/${endpoint}?${new URLSearchParams(params)}`)).json();}

// Present adjacent slots together without changing the stored reservations.
export function groupBookings(bookings) {
 const groups=[];
 const ordered=[...bookings].sort((a,b)=>String(a.location_id).localeCompare(String(b.location_id))||String(a.status).localeCompare(String(b.status))||Date.parse(a.start_time)-Date.parse(b.start_time));
 const date=t=>new Date(Date.parse(t)+8*3600000).toISOString().slice(0,10);
 for(const booking of ordered){
  const last=groups.at(-1);
  if(last&&last.location_id===booking.location_id&&last.status===booking.status&&date(last.start_time)===date(booking.start_time)&&Date.parse(last.end_time)===Date.parse(booking.start_time)){
   last.end_time=booking.end_time;last.booking_ids.push(booking.booking_id);
  }else groups.push({...booking,booking_ids:[booking.booking_id]});
 }
 return groups.sort((a,b)=>Date.parse(b.start_time)-Date.parse(a.start_time));
}
