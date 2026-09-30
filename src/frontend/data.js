export const band = ratio => ratio == null ? 'unknown' : ratio <= .3 ? 'quiet' : ratio <= .7 ? 'moderate' : 'crowded';
export function dayEvents(events,date) {return events.filter(e=>Date.parse(e.start_time)<Date.parse(`${date}T23:59:59+08:00`)&&Date.parse(e.end_time)>Date.parse(`${date}T00:00:00+08:00`));}
async function get(url){const r=await fetch(url,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw new Error(`API request failed (${r.status}). Check that the backend is running.`);return r;}
export async function api(endpoint,params={}) {return (await get(`/api/${endpoint}?${new URLSearchParams(params)}`)).json();}
