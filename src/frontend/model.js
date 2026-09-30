// Original low-poly campus geometry. Projected from 3D coordinates into SVG;
// illustrative massing, not a surveyed architectural/floor-plan model.
const shapes={
 E2:{x:180,y:-125,w:190,d:66,wings:true},
 E6:{x:250,y:95,w:145,d:72,wings:true},
 W1:{x:-135,y:10,w:82,d:85,wings:false},
 W3:{x:-280,y:-100,w:115,d:65,wings:true},
 W5:{x:-280,y:100,w:115,d:65,wings:true}
};
const palette={quiet:'#4b956d',moderate:'#c69640',crowded:'#be685a',unknown:'#99a49d'};
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let angle=-.32,zoom=1,tilt=.55;
export function adjustModel(action){if(action==='left')angle-=.22;if(action==='right')angle+=.22;if(action==='in')zoom=Math.min(1.6,zoom+.15);if(action==='out')zoom=Math.max(.65,zoom-.15);if(action==='reset'){angle=-.32;zoom=1;tilt=.55;}}
// Bind once to the stable container: SVG children are replaced during rendering.
export function bindModelGestures(host,redraw){
 let pointer=null,dragging=false,frame=0,suppressClick=false;
 const repaint=()=>{if(!frame)frame=requestAnimationFrame(()=>{frame=0;redraw();});};
 host.addEventListener('pointerdown',e=>{
   if(e.button!==0||e.isPrimary===false)return;
   suppressClick=false;
   pointer={id:e.pointerId,x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY};
 });
 host.addEventListener('pointermove',e=>{
   if(!pointer||pointer.id!==e.pointerId)return;
   if(!dragging&&Math.hypot(e.clientX-pointer.startX,e.clientY-pointer.startY)<5)return;
   if(!dragging){dragging=true;host.setPointerCapture(e.pointerId);host.classList.add('dragging');}
   angle+=(e.clientX-pointer.x)*.008;
   tilt=Math.max(.25,Math.min(.85,tilt+(e.clientY-pointer.y)*.003));
   pointer.x=e.clientX;pointer.y=e.clientY;
   e.preventDefault();repaint();
 });
 const finish=e=>{
   if(!pointer||pointer.id!==e.pointerId)return;
   suppressClick=dragging;pointer=null;dragging=false;host.classList.remove('dragging');
   if(host.hasPointerCapture(e.pointerId))host.releasePointerCapture(e.pointerId);
 };
 host.addEventListener('pointerup',finish);
 host.addEventListener('pointercancel',finish);
 host.addEventListener('lostpointercapture',finish);
 host.addEventListener('pointerleave',e=>{if(!dragging)finish(e);});
 host.addEventListener('click',e=>{if(suppressClick){e.preventDefault();e.stopImmediatePropagation();suppressClick=false;}},true);
 host.addEventListener('wheel',e=>{
   e.preventDefault();
   const units=e.deltaMode===1?16:e.deltaMode===2?host.clientHeight:1;
   const delta=Math.max(-150,Math.min(150,e.deltaY*units));
   zoom=Math.max(.65,Math.min(1.6,zoom*Math.exp(-delta*(e.ctrlKey?.008:.002))));
   repaint();
 },{passive:false});
}
export function renderModel(state,filtered,onBuilding,onFloor,onRoom){
 const host=document.getElementById('campus-model');
 const focus=shapes[state.building],scale=(focus?2.05:1)*zoom;
 const project=(x,y,z=0)=>{x-=focus?.x||0;y-=focus?.y||0;const xx=x*Math.cos(angle)-y*Math.sin(angle),yy=x*Math.sin(angle)+y*Math.cos(angle);return [450+xx*scale,330+yy*tilt*scale-z*scale];};
 const point=p=>p.map(n=>n.toFixed(2)).join(',');
 const poly=(points,fill,stroke='#ffffff50')=>`<polygon points="${points.map(p=>point(project(...p))).join(' ')}" fill="${fill}" stroke="${stroke}" stroke-width=".7"/>`;
 const box=(x,y,w,d,z,h,tone)=>{
   const a=[x-w/2,y-d/2,z],b=[x+w/2,y-d/2,z],c=[x+w/2,y+d/2,z],e=[x-w/2,y+d/2,z];
   // Choose camera-facing walls in every quadrant, instead of always +X/+Y.
   const wall=(u,v,t)=>poly([u,v,[v[0],v[1],z+h],[u[0],u[1],z+h]],t);
   return (Math.cos(angle)>=0?wall(e,c,tone[1]):wall(a,b,tone[1]))
     +(Math.sin(angle)>=0?wall(b,c,tone[2]):wall(a,e,tone[2]))
     +poly([[a[0],a[1],z+h],[b[0],b[1],z+h],[c[0],c[1],z+h],[e[0],e[1],z+h]],tone[0]);
 };
 let svg=`<svg viewBox="0 0 900 570" aria-label="Original interactive campus model" role="group"><defs><radialGradient id="ground"><stop stop-color="#f3f6e9"/><stop offset="1" stop-color="#dde6d8"/></radialGradient></defs><rect width="900" height="570" fill="url(#ground)"/>`;
 svg+=poly([[-390,-255,-3],[390,-255,-3],[390,255,-3],[-390,255,-3]],'#e5ecdd','#ced8c5');
 // Authored landscape and circulation, inspired by the wayfinder's visual language.
 // These paths are illustrative scenery, not a navigation graph.
 const strip=(x,y,w,d,fill,z=0)=>poly([[x-w/2,y-d/2,z],[x+w/2,y-d/2,z],[x+w/2,y+d/2,z],[x-w/2,y+d/2,z]],fill,'none');
 svg+=strip(0,216,780,32,'#c3cbc9')+strip(0,194,780,9,'#fbf8ef');
 for(let x=-370;x<380;x+=34)svg+=strip(x,216,17,1.5,'#edf0e9');
 svg+=strip(0,0,745,28,'#f9f5e9')+strip(35,0,24,385,'#f9f5e9');
 for(const [x,y,w,d] of [[-130,-120,36,165],[80,-90,28,125],[-135,105,30,140],[150,135,125,22]])svg+=strip(x,y,w,d,'#faf6eb');
 for(const [x,y,w,d] of [[-60,-140,95,62],[70,100,75,95],[-310,95,22,110],[300,-160,105,25]]){
   svg+=box(x,y,w,d,0,2,['#b7ce98','#98b77e','#a4bf89']);
   for(let dx=-w/2+9;dx<w/2;dx+=15)svg+=strip(x+dx,y,4,d-8,'#a8c68d',2.2);
 }
 // Paved forecourts, bench seating and pedestrian crossings.
 for(const [x,y] of [[-45,95],[170,-35],[-230,-5],[250,130]]){
   svg+=strip(x,y,66,28,'#e8ddc8');
   for(let k=-2;k<=2;k++)svg+=strip(x+k*12,y,1,27,'#d8cbb2',.1);
   svg+=box(x-20,y+9,18,5,1,3,['#ad9471','#8d7659','#7b674e']);
 }
 for(let k=0;k<6;k++)svg+=strip(26+k*4,216,2,22,'#fffdf3',.2);
 const trees=[];
 for(let x=-350;x<=350;x+=28)trees.push([x,180],[x,-210]);
 for(let y=-170;y<=135;y+=28)trees.push([-355,y],[355,y]);
 trees.push([-90,-130],[-60,-150],[-25,-130],[70,90],[85,120],[-135,150],[105,-145]);
 for(const [x,y] of trees){const [px,py]=project(x,y,11);svg+=`<ellipse cx="${px+4*scale}" cy="${py+11*scale}" rx="${11*scale}" ry="${5*scale}" fill="#617d5425"/><path d="M${px},${py+11*scale}v${-10*scale}" stroke="#8b8163" stroke-width="${2*scale}"/><circle cx="${px}" cy="${py}" r="${8*scale}" fill="#88aa72"/><circle cx="${px-3*scale}" cy="${py-3*scale}" r="${6*scale}" fill="#aac88f"/>`;}
 // Reference landmarks provide context only; they have no occupancy records.
 const scene=[];
 const depth=(x,y)=>x*Math.sin(angle)+y*Math.cos(angle);
 let contextLabels='';
 const landmark=(x,y,w,d,h,label,tone)=>{
   scene.push({depth:depth(x,y),markup:box(x,y,w,d,0,h,tone)});
   const [px,py]=project(x,y,h+14);
   contextLabels+=`<text x="${px}" y="${py}" text-anchor="middle" class="landmark-label">${label}</text>`;
 };
 if(!focus){
   // Solid tower shell, inset curtain wall and camera-facing fins.
   // Massing follows the public reference; dimensions remain illustrative.
   const tx=100,ty=58,tw=68,td=77,th=92;
   let tower=box(tx,ty,tw+8,td+8,0,5,['#dce0d3','#bdc8bd','#9cafab']);
   tower+=box(tx,ty,tw,td,5,th-5,['#e5e9e4','#718d9a','#526e7f']);
   const sy=Math.cos(angle)>=0?1:-1,sx=Math.sin(angle)>=0?1:-1;
   for(let z=13;z<th;z+=8){
     tower+=poly([[tx-tw/2,ty+sy*td/2,z],[tx+tw/2,ty+sy*td/2,z],[tx+tw/2,ty+sy*td/2,z+.8],[tx-tw/2,ty+sy*td/2,z+.8]],'#b5c8cd','none');
     tower+=poly([[tx+sx*tw/2,ty-td/2,z],[tx+sx*tw/2,ty+td/2,z],[tx+sx*tw/2,ty+td/2,z+.8],[tx+sx*tw/2,ty-td/2,z+.8]],'#a2b8c1','none');
   }
   for(let k=0;k<10;k++)tower+=box(tx-tw/2+3+k*(tw-6)/9,ty+sy*(td/2+1),1.8,3,6,th-7,['#edf0e9','#d8e2df','#aabdc4']);
   for(let k=0;k<11;k++)tower+=box(tx+sx*(tw/2+1),ty-td/2+3+k*(td-6)/10,3,1.8,6,th-7,['#edf0e9','#d8e2df','#aabdc4']);
   tower+=box(tx,ty,tw+2,td+2,th,2,['#e7ebe5','#d4dfd9','#bdcdcb']);
   tower+=box(tx+8,ty-7,28,30,th+2,5,['#f4f4eb','#dce3da','#bdcdc6']);
   tower+=box(tx-12,ty+10,19,24,th+2,1,['#96b2bd','#7897a3','#607f8f']);
   scene.push({depth:depth(tx,ty),markup:`<g aria-label="E1 University Tower reference model">${tower}</g>`});
   const towerLabel=project(tx,ty,th+20);
   contextLabels+=`<text x="${towerLabel[0]}" y="${towerLabel[1]}" text-anchor="middle" class="landmark-label">E1 · University Tower</text>`;
   landmark(310,-118,45,66,37,'E3 · Ho Bee Auditorium',['#bca471','#99805c','#777066']);
   landmark(345,-20,48,76,23,'E4 · Food Court',['#edece2','#c8d2c3','#a7bba9']);
   landmark(310,35,74,64,39,'E5 · Multi-Purpose Hall',['#e0e3e0','#becbc6','#a1b5b1']);
   const road=project(12,120,1);
   contextLabels+=`<text x="${road[0]}" y="${road[1]}" text-anchor="middle" class="landmark-label">Campus Boulevard</text>`;
   const coast=project(160,236,1);
   contextLabels+=`<text x="${coast[0]}" y="${coast[1]}" text-anchor="middle" class="landmark-label">Punggol Coast Road</text>`;
 }
 // Bridge endpoints are schematic, not a surveyed or routable floor plan.
 // E6–E1 is documented by SIT; western spans illustrate the Level 5 loop.
 const bridges=[
   {from:'E6',to:'E1',points:[[178,95],[146,95],[134,78]],name:'L5 · E6–E1 link'},
   {from:'W3',to:'W1',points:[[-223,-100],[-177,-100],[-177,-10]],name:'L5 · Collaboration Loop'},
   {from:'W1',to:'W5',points:[[-176,35],[-177,100],[-223,100]],name:'L5 · Collaboration Loop'}
 ];
 const bridgeSegment=(a,b,z)=>{
   const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy),nx=-dy/len*6,ny=dx/len*6;
   const corners=[[a[0]+nx,a[1]+ny],[b[0]+nx,b[1]+ny],[b[0]-nx,b[1]-ny],[a[0]-nx,a[1]-ny]];
   let result=poly(corners.map(([x,y])=>[x,y,z]),'#c3a56d','#8d764e');
   for(const sign of [-1,1]){
     result+=poly([[a[0]+nx*sign,a[1]+ny*sign,z-3],[b[0]+nx*sign,b[1]+ny*sign,z-3],[b[0]+nx*sign,b[1]+ny*sign,z],[a[0]+nx*sign,a[1]+ny*sign,z]],'#9b855d');
     const line=(height)=>[project(a[0]+nx*sign,a[1]+ny*sign,z+height),project(b[0]+nx*sign,b[1]+ny*sign,z+height)].map(point).join(' ');
     result+=`<polyline points="${line(7)}" fill="none" stroke="#687b76" stroke-width="1.6"/>`;
     for(let t=0;t<=1;t+=.15){const x=a[0]+dx*t+nx*sign,y=a[1]+dy*t+ny*sign;result+=`<polyline points="${point(project(x,y,z))} ${point(project(x,y,z+7))}" stroke="#81958a" stroke-width="1"/>`;}
   }
   return result;
 };
 const drawBridges=()=>{
   let result='';
   for(const bridge of bridges){
     if(focus&&bridge.from!==state.building&&bridge.to!==state.building)continue;
     if(focus&&state.floor!=='all'&&String(state.floor)!=='5')continue;
     const z=focus?79:44;
     result+=`<g class="campus-bridge"><title>${bridge.name} · schematic alignment</title>`;
     for(let i=1;i<bridge.points.length;i++)result+=bridgeSegment(bridge.points[i-1],bridge.points[i],z);
     const mid=bridge.points[1],label=project(mid[0],mid[1],z+15);
     result+=`<text x="${label[0]}" y="${label[1]}" text-anchor="middle" class="bridge-label">${bridge.name}</text></g>`;
   }
   return result;
 };
 const buildings=state.buildings.filter(b=>shapes[b.building_id]).sort((a,b)=>{const aa=shapes[a.building_id],bb=shapes[b.building_id];return (aa.x-bb.x)*Math.sin(angle)+(aa.y-bb.y)*Math.cos(angle);});
 let markers='';
 for(const building of buildings){
   const id=building.building_id,s=shapes[id],selected=id===state.building;
   if(focus&&!selected)continue;
   const sceneStart=svg.length;
   const locations=state.locations.filter(l=>l.building_id===id),levels=[...new Set(locations.map(r=>Number(r.floor)))].sort((a,b)=>a-b);
   const max=Math.max(5,...levels),expanded=!!focus;
   svg+=`<g class="model-building" ${expanded?'':`tabindex="0" role="button" aria-label="Explore ${safe(building.name)}" data-model-building="${safe(id)}"`}>`;
   svg+=box(s.x,s.y,s.w+14,s.d+14,0,4,['#d2d9bf','#b1bf9f','#9fab90']);
   for(let f=1;f<=max;f++){
     const top=expanded?f*15:f*8,active=String(state.floor)===String(f),mapped=levels.includes(f)||f===5;
     const tones=active?['#e3d5a6','#bca46a','#a38a53']:mapped?['#eef0dc','#c4d0be','#a8bcae']:['#e5eadf','#d1dacd','#becdc0'];
     const opacity=expanded&&state.floor!=='all'&&!active?.22:1;
     svg+=`<g opacity="${opacity}" ${expanded&&mapped?`class="model-level" tabindex="0" role="button" aria-label="View Level ${f}" data-model-floor="${f}"`:''}>`;
     svg+=box(s.x,s.y,s.w,s.d,top,4,tones);
     if(!expanded){
       svg+=box(s.x,s.y,s.w-5,s.d-5,top+4,4,['#d7e1dd','#74929b','#536f7d']);
       // Repeated facade fins, glazing and planted balcony strips.
       for(let k=-s.w/2+8;k<s.w/2-3;k+=12)svg+=box(s.x+k,s.y+s.d/2-2,2,3,top+4,4,['#f6f5eb','#e9eadf','#b8c8c6']);
       if(f%3===0)svg+=box(s.x+s.w*.12,s.y+s.d/2+1,s.w*.6,6,top+3,3,['#86ac68','#709654','#5c8348']);
     }
     if(s.wings && !expanded)svg+=box(s.x-s.w*.35,s.y+s.d*.38,s.w*.3,s.d*.48,top,7,tones);
     if(expanded&&mapped){const [lx,ly]=project(s.x-s.w/2-12,s.y+s.d/2,top+4);svg+=`<text x="${lx}" y="${ly}" class="floor-label">L${f}</text>`;}
     svg+='</g>';
   }
   if(!expanded){
     const roof=max*8+8;
     svg+=box(s.x,s.y,s.w-4,s.d-4,roof,2,['#edf0e8','#cad5cd','#aebfbd']);
     // Individually drawn rooftop solar modules, skylights and service core.
     for(let row=0;row<3;row++)for(let col=0;col<7;col++){
       svg+=box(s.x-s.w*.34+col*s.w*.085,s.y-s.d*.27+row*s.d*.17,s.w*.077,s.d*.14,roof+2,1,['#435c7d','#344b65','#293e56']);
     }
     svg+=box(s.x+s.w*.34,s.y-s.d*.14,s.w*.13,s.d*.36,roof+2,7,['#faf9f1','#d7dfd6','#becdc6']);
     svg+=box(s.x+s.w*.25,s.y+s.d*.30,s.w*.32,s.d*.13,roof+2,2,['#9abd7d','#7ba25e','#6c9253']);
     // Entrance glazing, projecting canopy and steps distinguish ground level.
     svg+=box(s.x+s.w*.18,s.y+s.d/2+2,s.w*.23,5,4,9,['#a9c4cb','#779eab','#527886']);
     svg+=box(s.x+s.w*.18,s.y+s.d/2+9,s.w*.32,19,13,2,['#f7f4e6','#d8d7c7','#b9c6bf']);
     for(let step=0;step<3;step++)svg+=box(s.x+s.w*.18,s.y+s.d/2+15+step*3,s.w*.35,4,0,3-step*.7,['#dedfce','#c1c8b9','#b0bbac']);
   }
   svg+='</g>';
   scene.push({depth:depth(s.x,s.y),markup:svg.slice(sceneStart)});
   svg=svg.slice(0,sceneStart);
   if(!focus){const [px,py]=project(s.x,s.y,max*8+30);markers+=`<g class="model-tag" tabindex="0" role="button" aria-label="Explore ${safe(building.name)}" data-model-building="${id}" transform="translate(${px},${py})"><rect x="-43" y="-18" width="86" height="36" rx="9"/><text text-anchor="middle" y="-2">${id==='W1'?'W1 · Library':id}</text><text text-anchor="middle" y="11" class="tag-sub">${locations.length} spaces ↗</text></g>`;}
   if(focus){
     const allValid=locations.filter(r=>r.map_x!=null&&r.map_y!=null&&r.map_x!==''&&r.map_y!=='');
     const xs=allValid.map(r=>Number(r.map_x)),ys=allValid.map(r=>Number(r.map_y));
     const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
     for(const r of filtered.filter(r=>r.building_id===id && r.map_x!=null&&r.map_y!=null&&r.map_x!==''&&r.map_y!=='')){
       const rx=Number(r.map_x),ry=Number(r.map_y);if(!Number.isFinite(rx)||!Number.isFinite(ry)||rx<0||rx>1||ry<0||ry>1)continue;
       const x=s.x+((rx-minX)/(maxX-minX||1)-.5)*s.w*.7,y=s.y+((ry-minY)/(maxY-minY||1)-.5)*s.d*.65;
       const [px,py]=project(x,y,Number(r.floor)*15+12),colour=palette[r.crowd_level]||palette.unknown;
       markers+=`<g class="model-room ${state.selected===r.location_id?'selected':''}" tabindex="0" role="button" aria-label="${safe(r.name)}, Level ${safe(r.floor)}, ${safe(r.crowd_level||'unknown')}" data-model-room="${safe(r.location_id)}" transform="translate(${px},${py})"><title>${safe(r.name)} · L${safe(r.floor)} · ${r.occupancy_ratio==null?'Unknown':Math.round(r.occupancy_ratio*100)+'%'} · ${safe(r.crowd_level||'unknown')}</title><circle r="15" fill="${colour}" opacity=".18"/><circle r="7" fill="${colour}" stroke="white" stroke-width="2"/><text y="-15" text-anchor="middle">${safe(r.name)}</text></g>`;
     }
   }
 }
 svg+=scene.sort((a,b)=>a.depth-b.depth).map(item=>item.markup).join('');
 svg+=drawBridges()+contextLabels+markers+`<text x="24" y="539" class="model-footnote">${focus?'Select a floor or a crowd marker':'CAMPUS WEST + EAST · ILLUSTRATIVE LANDSCAPE'}</text></svg>`;
 host.innerHTML=svg;
 const bind=(selector,fn)=>host.querySelectorAll(selector).forEach(el=>{const activate=e=>{e.stopPropagation();fn(el);};el.onclick=activate;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate(e);}};});
 bind('[data-model-building]',el=>{if(el.dataset.modelBuilding!==state.building)onBuilding(el.dataset.modelBuilding);});
 bind('[data-model-floor]',el=>onFloor(el.dataset.modelFloor));
 bind('[data-model-room]',el=>onRoom(el.dataset.modelRoom));
 const floors=focus?[...new Set([5,...state.locations.filter(l=>l.building_id===state.building).map(l=>Number(l.floor))])].sort((a,b)=>a-b):[];
 document.getElementById('model-floors').innerHTML=focus?['all',...floors].map(f=>`<button data-model-select-floor="${f}" class="${String(state.floor)===String(f)?'active':''}" aria-pressed="${String(state.floor)===String(f)}">${f==='all'?'All levels':'Level '+f}</button>`).join(''):'<span>Choose E2, E6, W1, W3 or W5 to explore its floors.</span>';
 document.querySelectorAll('[data-model-select-floor]').forEach(el=>el.onclick=()=>onFloor(el.dataset.modelSelectFloor));
}
