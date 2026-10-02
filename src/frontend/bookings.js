// Demo reservations use actual Singapore time, independently of the map clock.
const $=id=>document.getElementById(id);
let user=null, chosenRoom=null, slots=[], loadVersion=0, weekly=null, selected=new Set(), submitting=false;
const format=t=>new Intl.DateTimeFormat('en-SG',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Singapore'}).format(new Date(t));
const clock=t=>new Intl.DateTimeFormat('en-SG',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Singapore'}).format(new Date(t));
const day=offset=>new Date(Date.now()+8*3600000+offset*86400000).toISOString().slice(0,10);
async function request(path,body){
 const response=await fetch('/api/'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:body===undefined?{}:{'Content-Type':'application/json','X-Occuscope-Request':'1'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
 const data=await response.json();
 if(!response.ok){const e=new Error(typeof data.detail==='string'?data.detail:'Check your details and try again.');e.status=response.status;throw e;}
 return data;
}
const accountButton=document.createElement('button');
accountButton.id='student-account';accountButton.className='account-button';accountButton.textContent='Student login';
document.querySelector('.topbar').append(accountButton);
document.body.insertAdjacentHTML('beforeend',`
<dialog id="account-dialog" class="booking-dialog student-login" aria-labelledby="account-title">
 <div class="login-layout">
  <aside class="login-story"><span class="login-brand">◉ occuscope.</span><span class="login-chip">YOUR CAMPUS COMPANION</span><h2>A little space.<br>A lot of possibility.</h2><p>Find your focus, connect with your campus, and make room for a good day.</p><div class="login-art" aria-hidden="true"><i></i><i></i><i></i><span>✦</span></div><small>SIT PUNGGOL · STUDENT PORTAL</small></aside>
  <div class="login-content"><button class="login-close" type="button" data-dismiss="account-dialog" aria-label="Close account">✕</button>
   <p class="eyebrow">WELCOME TO YOUR SPACE</p><h2 id="account-title">Welcome back.</h2><p id="login-subtitle" class="login-subtitle">Sign in with your student email to get started.</p>
   <form id="account-form"><label>Student email<input id="account-email" type="email" autocomplete="username" placeholder="2500001@sit.singaporetech.edu.sg" maxlength="254" required></label><label>Password<span class="password-field"><input id="account-password" type="password" autocomplete="current-password" minlength="10" maxlength="128" placeholder="Enter your password" required><button id="password-toggle" type="button" aria-label="Show password" aria-pressed="false">Show</button></span></label><button id="account-submit" class="booking-primary">Sign in <span aria-hidden="true">↗</span></button></form>
   <div id="account-signed-in" hidden><div class="student-profile"><span id="student-avatar" aria-hidden="true"></span><div><strong id="student-name"></strong><p id="student-number"></p></div></div><p id="account-identity"></p><button id="account-logout" class="booking-secondary">Sign out</button><h3>My discussion-room bookings</h3><p class="booking-note">Reservations exist only in Occuscope. They do not reserve rooms in SIT’s official booking system.</p><div id="my-bookings"></div></div>
   <p id="account-status" role="status" aria-live="polite"></p><p class="login-footnote">Fictional accounts for this project. Not connected to SIT sign-in.</p>
  </div>
 </div>
</dialog>
<dialog id="booking-dialog" class="booking-dialog" aria-labelledby="booking-title">
 <div class="booking-heading"><div><p class="eyebrow">DISCUSSION ROOMS ONLY</p><h2 id="booking-title">Book a room</h2></div><button type="button" data-dismiss="booking-dialog" aria-label="Close booking">✕</button></div>
 <p class="booking-note">Demo rules: 08:00–20:00 SGT · 30-minute slots · 240 minutes per student per week (Monday–Sunday SGT) · next 14 days. Booking uses actual Singapore time, independently of the map’s viewing date. Occupancy colours do not indicate booking availability.</p>
 <form id="booking-form"><label>Booking date · SGT<input id="booking-date" type="date" required></label><div id="booking-allowance" class="booking-allowance" aria-live="polite"></div><fieldset class="slot-fieldset"><legend>Select 30-minute blocks · SGT</legend><p class="booking-note">Choose one or more blocks. They do not have to be consecutive.</p><div id="booking-slots" class="booking-slots"></div></fieldset><p id="booking-selection" aria-live="polite"></p><p class="booking-note">This reserves a room in the Occuscope demo only.</p><button id="booking-submit" class="booking-primary">Confirm demo booking</button></form>
 <p id="booking-status" role="status" aria-live="polite"></p><button id="booking-view-mine" class="booking-secondary" hidden>View my bookings</button>
</dialog>`);
for(const button of document.querySelectorAll('[data-dismiss]'))button.onclick=()=>$(button.dataset.dismiss).close();
$('password-toggle').onclick=()=>{const visible=$('account-password').type==='password';$('account-password').type=visible?'text':'password';$('password-toggle').textContent=visible?'Hide':'Show';$('password-toggle').setAttribute('aria-label',visible?'Hide password':'Show password');$('password-toggle').setAttribute('aria-pressed',String(visible));};
function accountState(){
 $('account-form').hidden=!!user;$('account-signed-in').hidden=!user;
 $('account-title').textContent=user?'Your campus account.':'Welcome back.';
 $('login-subtitle').textContent=user?'A little more room to make the most of campus.':'Sign in with your student email to get started.';
 $('account-dialog').classList.toggle('is-signed-in',!!user);
 accountButton.textContent=user?'My account':'Student login';
 if(user){$('account-identity').textContent=user.email;$('student-name').textContent=user.display_name||'Student';$('student-number').textContent='Student ID · '+user.student_id;$('student-avatar').textContent=(user.display_name||'S').split(' ').map(n=>n[0]).slice(0,2).join('');}
}
async function showAccount(){
 $('booking-dialog').close();$('account-status').textContent='';accountState();
 if(!$('account-dialog').open)$('account-dialog').showModal();
 if(user)await myBookings();
}
accountButton.onclick=()=>{chosenRoom=null;showAccount();};
$('account-form').onsubmit=async event=>{
 event.preventDefault();$('account-submit').disabled=true;$('account-submit').textContent='Signing in…';$('account-status').textContent='';
 try{user=await request('auth/login',{email:$('account-email').value,password:$('account-password').value});$('account-password').value='';accountState();
 if(chosenRoom){$('account-dialog').close();openBooking(chosenRoom);}else await myBookings();
 }catch(error){$('account-status').textContent=error.message;}finally{$('account-submit').disabled=false;$('account-submit').textContent='Sign in ↗';}
};
$('account-logout').onclick=async()=>{
 try{await request('auth/logout',{});user=null;chosenRoom=null;$('my-bookings').replaceChildren();accountState();$('account-status').textContent='Signed out.';}catch(error){$('account-status').textContent=error.message;}
};
async function myBookings(){
 $('my-bookings').textContent='Loading your bookings…';
 try{const bookings=await request('bookings/mine');$('my-bookings').replaceChildren();
 if(!bookings.length)$('my-bookings').textContent='No bookings yet. Select a discussion room on the map to get started.';
 for(const booking of bookings){
 const card=document.createElement('article');card.className='booking-card';
 const title=document.createElement('strong');title.textContent=booking.name+' · '+booking.building_id;
 const detail=document.createElement('p');detail.textContent=format(booking.start_time)+' – '+clock(booking.end_time)+' SGT';
 const status=document.createElement('p');status.textContent=booking.status;
 card.append(title,detail,status);
 if(booking.status==='confirmed'&&Date.parse(booking.start_time)>Date.now()){
 const cancel=document.createElement('button');cancel.className='booking-secondary';cancel.textContent='Cancel booking';
 cancel.onclick=async()=>{if(!confirm('Cancel this discussion-room booking?'))return;cancel.disabled=true;try{await request('bookings/'+encodeURIComponent(booking.booking_id)+'/cancel',{});await myBookings();}catch(error){$('account-status').textContent=error.message;cancel.disabled=false;}};
 card.append(cancel);
 }$('my-bookings').append(card);
 }
 }catch(error){$('my-bookings').textContent=error.message;if(error.status===401){user=null;accountState();}}
}
export function mountBookingAction(room){
 const section=document.createElement('div');section.className='room-booking-action';
 if(room.type==='discussion_room'){
 const button=document.createElement('button');button.className='booking-primary';button.textContent='Book discussion room';button.onclick=()=>openBooking(room);section.append(button);
 }else{const note=document.createElement('p');note.className='booking-note';note.textContent='Walk-in space · bookings are available for discussion rooms only.';section.append(note);}
 $('detail').append(section);
}
function openBooking(room){
 chosenRoom=room;
 if(!user){showAccount();return;}
 $('booking-title').textContent=room.name+' · '+room.building_id;
 $('booking-date').min=day(0);$('booking-date').max=day(14);$('booking-date').value=day(1);
 $('booking-form').hidden=false;$('booking-view-mine').hidden=true;$('booking-status').textContent='';
 if(!$('booking-dialog').open)$('booking-dialog').showModal();loadSlots();
}
async function loadSlots(){
 const version=++loadVersion;slots=[];weekly=null;selected.clear();$('booking-slots').replaceChildren();$('booking-allowance').textContent='';$('booking-selection').textContent='';$('booking-submit').disabled=true;$('booking-status').textContent='Checking booking availability…';
 try{const data=await request('bookings/availability?'+new URLSearchParams({location_id:chosenRoom.location_id,date:$('booking-date').value}));if(version!==loadVersion)return;slots=data.slots;weekly=data.weekly_allowance;if(!weekly)throw new Error('Sign in again to check your weekly allowance.');$('booking-status').textContent='';renderSlots();}
 catch(error){if(version===loadVersion){$('booking-status').textContent=error.message;if(error.status===401){user=null;accountState();showAccount();$('account-status').textContent='Your session expired. Please sign in again.';}}}
}
function renderSlots(){
 $('booking-slots').replaceChildren();
 const remaining=weekly?.remaining_minutes||0;
 if(weekly)$('booking-allowance').textContent=`${weekly.week_start} – ${weekly.week_end} · ${remaining} / 240 minutes remaining`;
 for(const slot of slots){
 const button=document.createElement('button');button.type='button';button.className='booking-slot';const checked=selected.has(slot.start_time);
 button.textContent=clock(slot.start_time)+' – '+clock(slot.end_time)+(slot.available?'':' · Unavailable');button.setAttribute('aria-pressed',String(checked));
 button.disabled=submitting||!slot.available||(!checked&&selected.size*30>=remaining);
 button.onclick=()=>{if(selected.has(slot.start_time))selected.delete(slot.start_time);else selected.add(slot.start_time);renderSlots();};$('booking-slots').append(button);
 }
 $('booking-selection').textContent=`${selected.size} blocks selected · ${selected.size*30} minutes · ${Math.max(0,remaining-selected.size*30)} minutes left after booking`;
 $('booking-submit').disabled=submitting||!selected.size||selected.size*30>remaining;
 if(!remaining)$('booking-status').textContent='You have used all 240 minutes for this week. Choose a date in another week or cancel an upcoming booking.';
}
$('booking-date').onchange=loadSlots;
$('booking-form').onsubmit=async event=>{
 event.preventDefault();if(submitting||!selected.size)return;
 submitting=true;$('booking-date').disabled=true;renderSlots();
 try{const result=await request('bookings',{location_id:chosenRoom.location_id,slots:[...selected].sort()});$('booking-form').hidden=true;$('booking-status').textContent=`${result.bookings.length} blocks confirmed · ${result.booked_minutes} minutes.\n`+result.bookings.map(b=>format(b.start_time)+' – '+clock(b.end_time)+' SGT').join('\n');$('booking-view-mine').hidden=false;}
 catch(error){if(error.status===401){user=null;accountState();showAccount();$('account-status').textContent='Your session expired. Sign in and choose your blocks again.';}else{await loadSlots();$('booking-status').textContent=error.message;}}
 finally{submitting=false;$('booking-date').disabled=false;if(!$('booking-form').hidden)renderSlots();}
};
$('booking-view-mine').onclick=()=>{chosenRoom=null;showAccount();};
request('auth/me').then(data=>{user=data;accountState();}).catch(error=>{if(error.status!==401)$('account-status').textContent=error.message;});
