import {renderModel,adjustModel,bindModelGestures} from './model.js';
import {mountBookingAction} from './bookings.js';
import {api,band,dayEvents} from './data.js';
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state={building:'all',floor:'all',selected:null,rows:[],buildings:[],locations:[],events:[],version:0,detailVersion:0};

const SEED_START='2026-08-31';
const SEED_END='2026-12-27';
let liveTimer=null;
const time=t=>new Intl.DateTimeFormat('en-SG',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Singapore'}).format(new Date(t));
const at=()=>`${$('date').value}T${$('hour').value}:00:00+08:00`;
function singaporeParts(){
  const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Singapore',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',hourCycle:'h23'}).formatToParts(new Date());
  const get=t=>parts.find(p=>p.type===t).value;
  return {date:`${get('year')}-${get('month')}-${get('day')}`,hour:Number(get('hour'))};
}
function snapLiveClock(){
  let {date,hour}=singaporeParts();
  if(date<SEED_START)date=SEED_START;
  if(date>SEED_END)date=SEED_END;
  hour=Math.min(20,Math.max(8,hour));
  $('date').value=date;
  $('hour').value=String(hour).padStart(2,'0');
}
function setLive(on){
  $('live').checked=on;
  $('date').disabled=on;
  $('hour').disabled=on;
  $('clock-fields').classList.toggle('following',on);
  clearInterval(liveTimer);
  liveTimer=null;
  if(on){
    snapLiveClock();
    liveTimer=setInterval(()=>{if(!$('live').checked)return;snapLiveClock();refresh();},60000);
  }
}
const badge=r=>`<span class="badge ${esc(r.crowd_level||'unknown')}"><i class="${esc(r.crowd_level||'unknown')}"></i>${esc(r.crowd_level||'No data')}</span>`;
function bookingHoursOpen(){
  const hour=Number($('hour').value);
  return hour>=8&&hour<20;
}
function bookPill(r){
  if(r.type!=='discussion_room')return '';
  if(!bookingHoursOpen())return '<span class="book-pill">Closed</span>';
  return Number(r.booked)?`<span class="book-pill is-booked">Booked</span>`:`<span class="book-pill is-free">Available</span>`;
}
function bookingNote(r){
  if(r.type!=='discussion_room')return r.type==='food_court'?'Walk-in dining.': 'Walk-in space · no booking needed.';
  if(!bookingHoursOpen())return 'Booking hours: 08:00–20:00 SGT.';
  const booked=Number(r.booked)?'Booked this hour':'Available this hour';
  if(r.occupancy_count==null)return booked+' · occupancy unavailable.';
  return booked+(Number(r.occupancy_count)>0?' · currently occupied.':' · currently unoccupied.');
}
$('hour').innerHTML=Array.from({length:13},(_,i)=>{const h=String(i+8).padStart(2,'0');return `<option value="${h}">${h}:00</option>`;}).join('');
function validate(){const d=$('date');if(!d.value||d.value<d.min||d.value>d.max){$('notice').textContent='Choose a date between 31 August and 27 December 2026, the available data period.';return false;}return true;}
async function refresh(){
 if(!validate())return;
 const version=++state.version; ++state.detailVersion;
 state.rows=[]; render(); $('detail').innerHTML='<p class="detail-note">Loading selected time…</p>';
 $('notice').textContent='Loading campus data…';
 try{
   const [buildings,locations,rows,events]=await Promise.all([api('buildings'),api('locations'),api('occupancy/current',{at:at()}),api('events/today')]);
   if(version!==state.version)return;
   Object.assign(state,{rows,buildings,locations,events});
   $('notice').textContent='';render();await renderDetail();
 }catch(e){if(version!==state.version)return;state.rows=[];render();$('detail').innerHTML='<p class="detail-note">Occupancy could not be loaded.</p>';$('notice').innerHTML=`${esc(e.message)} <button id="retry">Try again</button>`;$('retry').onclick=refresh;}
}
function chooseFloor(floor){state.floor=String(floor);state.selected=null;render();renderDetail();}
function chooseBuilding(id){adjustModel('reset');state.building=id;state.floor='all';state.selected=null;render();renderDetail();}
function render(){
 $('all').classList.toggle('active',state.building==='all');
 $('buildings').innerHTML=state.buildings.map(b=>{const rooms=state.rows.filter(r=>r.building_id===b.building_id);const label=b.building_id==='W1'?'Library · W1':b.building_id==='E4'?'Foodgle · E4':b.building_id==='W3'?'Wholesome · W3':esc(b.name);return `<button class="building-row ${state.building===b.building_id?'active':''}" data-building="${esc(b.building_id)}" aria-pressed="${state.building===b.building_id}"><span class="building-icon">${esc(b.building_id)}</span><span><strong>${label}</strong><small>${rooms.length} mapped spaces</small></span><i class="${buildingBand(rooms)}"></i></button>`;}).join('');
 document.querySelectorAll('[data-building]').forEach(b=>b.onclick=()=>chooseBuilding(b.dataset.building));
 const chosen=state.buildings.find(b=>b.building_id===state.building);
 $('map-title').textContent=chosen?`${chosen.name}${state.floor==='all'?'':' · Level '+state.floor}`:'Explore SIT Punggol';
 $('map-kicker').textContent='OCCUSCOPE CAMPUS MODEL';
 $('selected-time').textContent=`${$('live').checked?'Following clock · ':''}${$('date').value} · ${$('hour').value}:00 SGT`;
 $('coordinate-title').textContent=`${chosen?chosen.name:'Campus'}${state.floor==='all'?'':' · Level '+state.floor}`;
 $('spaces-title').textContent=chosen?`${chosen.name} spaces`:'All campus spaces';
 const floors=[...new Set(state.locations.filter(l=>state.building==='all'||l.building_id===state.building).map(l=>Number(l.floor)))].sort((a,b)=>a-b);
 $('floors').innerHTML=['all',...floors].map(f=>`<button data-floor="${f}" class="${String(state.floor)===String(f)?'active':''}" aria-pressed="${String(state.floor)===String(f)}">${f==='all'?'All floors':'Level '+f}</button>`).join('');
 document.querySelectorAll('[data-floor]').forEach(b=>b.onclick=()=>chooseFloor(b.dataset.floor));
 const q=$('search').value.trim().toLowerCase();
 const bookFilter=$('booked').value;
 const rooms=state.rows.filter(r=>(state.building==='all'||r.building_id===state.building)&&(state.floor==='all'||String(r.floor)===String(state.floor))&&($('crowd').value==='all'||r.crowd_level===$('crowd').value)&&($('type').value==='all'||r.type===$('type').value)&&(bookFilter==='all'||(r.type==='discussion_room'&&bookingHoursOpen()&&((bookFilter==='booked'&&Number(r.booked))||(bookFilter==='available'&&!Number(r.booked)))))&&`${r.name} ${r.location_id} ${r.building_id} ${r.building_name||''} ${r.building_id==='W1'?'library':''} ${r.type==='food_court'?'foodgle wholesome canteen':''}`.toLowerCase().includes(q));
 $('result-count').textContent=`${rooms.length} spaces`;
 $('map-count').textContent=`${state.rows.length} spaces`;
 renderCoordinates(rooms);
 renderModel(state,rooms,chooseBuilding,chooseFloor,selectRoom);
 $('rooms').innerHTML=rooms.length?rooms.map(r=>`<button class="room-card ${state.selected===r.location_id?'selected':''}" data-room="${esc(r.location_id)}" aria-pressed="${state.selected===r.location_id}"><div class="room-card-top"><span>${esc(r.building_id)} / LEVEL ${esc(r.floor)}</span>${badge(r)}</div><h3>${esc(r.name)}</h3><p>${[esc(r.type.replaceAll('_',' ')),bookPill(r)].filter(Boolean).join(' · ')}</p><div class="meter ${esc(r.crowd_level)}"><span style="width:${Math.min(100,Math.max(0,(r.occupancy_ratio||0)*100))}%"></span></div><div class="room-card-bottom"><span>${r.occupancy_count==null?'No reading':`${esc(r.occupancy_count)} / ${esc(r.capacity)} people`}</span><span>View space ↗</span></div></button>`).join(''):'<p class="no-results">No spaces match this view. Try another floor or clear your filters.</p>';
 document.querySelectorAll('[data-room]').forEach(b=>b.onclick=()=>selectRoom(b.dataset.room));
 const eventDate=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Singapore',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const events=dayEvents(state.events,eventDate).filter(e=>state.building==='all'||state.locations.some(l=>l.location_id===e.location_id&&l.building_id===state.building));
 $('event-date').textContent=`${eventDate} · Today in Singapore`;
 $('events').innerHTML=events.length?events.map(e=>`<article class="event"><h3>${esc(e.title)}</h3><p>${time(e.start_time)}–${time(e.end_time)} SGT</p><button data-event-room="${esc(e.location_id)}">${esc(e.location_id)} ↗</button></article>`).join(''):'<p class="event fine-print">No listed events for this view.</p>';
 document.querySelectorAll('[data-event-room]').forEach(b=>b.onclick=()=>{const r=state.rows.find(r=>r.location_id===b.dataset.eventRoom);if(r){state.building=r.building_id;state.floor=String(r.floor);selectRoom(r.location_id);}});
}
function buildingBand(rooms){const known=rooms.filter(r=>r.occupancy_count!=null);if(!known.length)return 'unknown';return band(known.reduce((s,r)=>s+Number(r.occupancy_count),0)/known.reduce((s,r)=>s+Number(r.capacity),0));}
function selectRoom(id){const room=state.rows.find(r=>r.location_id===id);if(room){if(state.building!==room.building_id)adjustModel('reset');state.building=room.building_id;state.floor=String(room.floor);}state.selected=id;render();renderDetail();if(innerWidth<1100)$('detail').scrollIntoView({behavior:'smooth',block:'nearest'});}
async function renderDetail(){
 const version=++state.detailVersion;
 const r=state.rows.find(r=>r.location_id===state.selected);
 if(!r){$('detail').innerHTML='<div class="empty-detail"><span>⌖</span><h2>A spot with your name on it.</h2><p>Select a room below to explore its occupancy and daily rhythm.</p></div>';return;}
 $('detail').innerHTML=`<div class="detail-top"><p class="eyebrow">YOUR SELECTED SPACE</p><button id="close-detail" aria-label="Close location details">✕</button></div><div class="detail-pills">${badge(r)}${bookPill(r)}</div><h2>${esc(r.name)}</h2><p class="subtitle">${esc(r.building_id)} · Level ${esc(r.floor)} · ${esc(r.type.replaceAll('_',' '))}</p><div class="occupancy-number">${r.occupancy_count==null?'—':esc(r.occupancy_count)} <small>/ ${esc(r.capacity)} people</small></div><div class="meter ${esc(r.crowd_level)}"><span style="width:${Math.min(100,(r.occupancy_ratio||0)*100)}%"></span></div><p class="detail-note">${r.timestamp?`${Math.round(r.occupancy_ratio*100)}% occupancy<br>Reading: ${esc(r.timestamp.slice(0,10))}, ${time(r.timestamp)} SGT`:'No reading at this time.'}</p><p class="detail-note">${esc(bookingNote(r))}</p><p class="detail-note map-search-hint">Highlighted in our campus model: <strong>${esc(r.name)}</strong>, ${esc(r.building_id)}, Level ${esc(r.floor)}.</p><h3 class="chart-heading">The day's rhythm </h3><div id="history">Loading daily history…</div><div class="forecast" id="forecast">Loading forecast…</div>`;
 mountBookingAction(r);
 $('close-detail').onclick=()=>{state.selected=null;render();renderDetail();};
 try{
   let history,predictions;
   const date=$('date').value;
   const next=new Date(`${date}T00:00:00Z`);next.setUTCDate(next.getUTCDate()+1);
   [history,predictions]=await Promise.all([api(`occupancy/${encodeURIComponent(r.location_id)}`,{from:`${date}T00:00:00+08:00`,to:`${next.toISOString().slice(0,10)}T00:00:00+08:00`}),api(`occupancy/${encodeURIComponent(r.location_id)}/prediction`,{at:at()})]);
   if(version!==state.detailVersion)return;
   $('history').innerHTML=history.length?`<div class="chart" role="img" aria-label="Hourly estimated occupancy: ${esc(history.map(h=>`${time(h.timestamp)}: ${h.occupancy_count} people`).join('; '))}">${history.map(h=>`<span class="${h.timestamp.slice(11,13)===$('hour').value?'chosen':''}" style="height:${Math.max(3,Math.min(100,Number(h.occupancy_count)/Number(r.capacity)*100))}%" title="${time(h.timestamp)}: ${esc(h.occupancy_count)} people"></span>`).join('')}</div><div class="chart-labels"><span>${time(history[0].timestamp)}</span><span>Singapore time</span><span>${time(history.at(-1).timestamp)}</span></div>`:'<p class="detail-note">No history for this day.</p>';
   const future=predictions.filter(p=>Date.parse(p.predicted_for)>Date.parse(at())&&Date.parse(p.predicted_for)<=Date.parse(at())+7200000);
   $('forecast').innerHTML='<strong>Next two hours</strong>'+(future.length?future.map(p=>`${time(p.predicted_for)} · ${esc(p.occupancy_count)} people`).join('<br>'):'<span class="detail-note">No forecast available for this time.</span>');
 }catch(e){if(version!==state.detailVersion)return;$('history').textContent=e.message;$('forecast').textContent='Forecast unavailable.';}
}
$('all').onclick=()=>chooseBuilding('all');
['search','crowd','type','booked'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));
['date','hour'].forEach(id=>$(id).addEventListener('change',()=>{setLive(false);refresh();}));
$('live').onchange=()=>{if($('live').checked){setLive(true);refresh();}else setLive(false);};
$('reset').onclick=()=>{adjustModel('reset');state.building='all';state.floor='all';state.selected=null;$('search').value='';$('crowd').value='all';$('type').value='all';$('booked').value='all';setLive(true);refresh();};
setLive(true);
refresh();

function renderCoordinates(rooms){
 const valid=rooms.filter(r=>r.map_x!=null && r.map_y!=null && r.map_x!=='' && r.map_y!=='' && Number.isFinite(Number(r.map_x)) && Number.isFinite(Number(r.map_y)) && Number(r.map_x)>=0 && Number(r.map_x)<=1 && Number(r.map_y)>=0 && Number(r.map_y)<=1);
 const xs=valid.map(r=>Number(r.map_x)),ys=valid.map(r=>Number(r.map_y));
 const minX=state.building==='all'?0:Math.min(...xs)-.025,maxX=state.building==='all'?1:Math.max(...xs)+.025;
 const minY=state.building==='all'?0:Math.min(...ys)-.025,maxY=state.building==='all'?1:Math.max(...ys)+.025;
 $('crowd-plot').innerHTML=valid.length?valid.map(r=>`<button class="crowd-point ${esc(r.crowd_level||'unknown')} ${state.selected===r.location_id?'selected':''}" style="left:${8+84*(Number(r.map_x)-minX)/(maxX-minX)}%;top:${8+84*(Number(r.map_y)-minY)/(maxY-minY)}%" data-point="${esc(r.location_id)}" title="${esc(r.name)} · Level ${esc(r.floor)} · ${esc(r.crowd_level||'No data')}" aria-label="${esc(r.name)}, ${esc(r.building_id)}, Level ${esc(r.floor)}, ${r.occupancy_ratio==null?'no reading':Math.round(r.occupancy_ratio*100)+' percent occupancy'}, ${esc(r.crowd_level||'unknown')}"><span>${state.building==='all'?'':esc(r.name)}</span></button>`).join(''):'<p class="no-results">No mapped coordinates in this view. Spaces without coordinates remain in the list.</p>';
 document.querySelectorAll('[data-point]').forEach(b=>b.onclick=()=>selectRoom(b.dataset.point));
}
function mapView(model){
 $('model-panel').hidden=!model;$('crowd-panel').hidden=model;
 for(const [id,selected] of [['model-view',model],['crowd-view',!model]]){$(id).classList.toggle('active',selected);$(id).setAttribute('aria-pressed',String(selected));}
}
$('model-view').onclick=()=>mapView(true);
$('crowd-view').onclick=()=>mapView(false);
$('model-home').onclick=()=>chooseBuilding('all');
document.querySelectorAll('[data-camera]').forEach(b=>b.onclick=()=>{adjustModel(b.dataset.camera);render();});

bindModelGestures($('campus-model'),render);

// Replies are rendered as text, never executable model HTML.
const chatPanel=$('campus-chat');
function showChat(open){chatPanel.hidden=!open;$('chat-toggle').setAttribute('aria-expanded',String(open));if(open)$('chat-input').focus();else $('chat-toggle').focus();}
$('chat-toggle').onclick=()=>showChat(chatPanel.hidden);
$('chat-close').onclick=()=>showChat(false);
chatPanel.addEventListener('keydown',e=>{if(e.key==='Escape')showChat(false);});
function chatLine(text,kind){const line=document.createElement('p');line.className='chat-line '+kind;line.textContent=text;$('chat-messages').append(line);line.scrollIntoView({block:'nearest'});return line;}
chatLine('Hi, I’m Octopus! Ask me about crowd levels or rooms. Each question uses the date and time selected above.','assistant');
$('chat-form').onsubmit=async e=>{
 e.preventDefault();if($('chat-send').disabled)return;const message=$('chat-input').value.trim();if(!message)return;
 const instant=at();chatLine(message,'user');$('chat-input').value='';$('chat-send').disabled=true;
 const pending=chatLine('','assistant');
 const typing=document.createElement('span');typing.className='octopus-typing';
 const description=document.createElement('span');description.className='sr-only';description.textContent='Octopus is typing…';typing.append(description);
 const mascot=$('chat-toggle').querySelector('svg').cloneNode(true);typing.append(mascot);
 pending.append(typing);pending.scrollIntoView({block:'nearest'});
 try{
  const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,at:instant}),signal:AbortSignal.timeout(30000)});
  const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Unable to answer this question.');
  pending.textContent=data.answer+'\nViewing: '+instant;
  for(const id of data.location_ids||[]){const room=state.rows.find(r=>r.location_id===id);if(!room)continue;const button=document.createElement('button');button.className='chat-room';button.textContent=room.name+' · '+room.building_id+' ↗';button.onclick=()=>{if(at()!==instant){chatLine('The selected time has changed. Ask again for updated suggestions.','assistant');return;}selectRoom(id);mapView(true);showChat(false);};pending.append(document.createElement('br'),button);}
 }catch(error){pending.textContent=error.name==='TimeoutError'?'Octopus took too long. Try again.':error.message;}
 finally{$('chat-send').disabled=false;}
};

// Step back from room/floor to building, then campus; drags suppress clicks.
function stepBackMap(){
 if(state.building==='all')return;
 if(state.selected||state.floor!=='all'){adjustModel('reset');chooseFloor('all');}
 else chooseBuilding('all');
}
for(const id of ['campus-model','crowd-plot']) $(id).addEventListener('click',event=>{
 if(event.target.closest('button,a,[role="button"],[data-model-room],[data-model-building],[data-model-floor]'))return;
 stepBackMap();
});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'&&!document.querySelector('dialog[open]')&&!event.target.closest('#campus-chat'))stepBackMap();
});
