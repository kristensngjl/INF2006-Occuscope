// Original low-poly campus geometry. Projected from 3D coordinates into SVG;
// illustrative massing, not a surveyed architectural/floor-plan model.
const shapes={
 E2:{x:170,y:-100,w:155,d:78,wings:true},
 E6:{x:245,y:70,w:140,d:65,wings:false},
 W1:{x:-40,y:15,w:92,d:85,wings:false},
 W3:{x:-235,y:-70,w:130,d:65,wings:true},
 W5:{x:-225,y:100,w:120,d:65,wings:true}
};
const palette={quiet:'#4b956d',moderate:'#c69640',crowded:'#be685a',unknown:'#99a49d'};
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let angle=-.32,zoom=1;
export function adjustModel(action){if(action==='left')angle-=.22;if(action==='right')angle+=.22;if(action==='in')zoom=Math.min(1.6,zoom+.15);if(action==='out')zoom=Math.max(.65,zoom-.15);if(action==='reset'){angle=-.32;zoom=1;}}
export function renderModel(state,filtered,onBuilding,onFloor,onRoom){
 const host=document.getElementById('campus-model');
 const focus=shapes[state.building],scale=(focus?2.05:1)*zoom;
 const project=(x,y,z=0)=>{x-=focus?.x||0;y-=focus?.y||0;const xx=x*Math.cos(angle)-y*Math.sin(angle),yy=x*Math.sin(angle)+y*Math.cos(angle);return [450+xx*scale,330+yy*.55*scale-z*scale];};
 const point=p=>p.map(n=>n.toFixed(2)).join(',');
 const poly=(points,fill,stroke='#ffffff50')=>`<polygon points="${points.map(p=>point(project(...p))).join(' ')}" fill="${fill}" stroke="${stroke}" stroke-width=".7"/>`;
 const box=(x,y,w,d,z,h,tone)=>{
   const a=[x-w/2,y-d/2,z],b=[x+w/2,y-d/2,z],c=[x+w/2,y+d/2,z],e=[x-w/2,y+d/2,z];
   return poly([e,c,[c[0],c[1],z+h],[e[0],e[1],z+h]],tone[1])+poly([b,c,[c[0],c[1],z+h],[b[0],b[1],z+h]],tone[2])+poly([[a[0],a[1],z+h],[b[0],b[1],z+h],[c[0],c[1],z+h],[e[0],e[1],z+h]],tone[0]);
 };
 let svg=`<svg viewBox="0 0 900 570" aria-label="Original interactive campus model" role="group"><defs><radialGradient id="ground"><stop stop-color="#f3f6e9"/><stop offset="1" stop-color="#dde6d8"/></radialGradient></defs><rect width="900" height="570" fill="url(#ground)"/>`;
 svg+=poly([[-390,-255,-3],[390,-255,-3],[390,255,-3],[-390,255,-3]],'#e5ecdd','#ced8c5');
 for(let x=-350;x<=350;x+=50)svg+=poly([[x,-240,-2],[x+1,-240,-2],[x+1,240,-2],[x,240,-2]],'#d9e2d0','none');
 for(let y=-220;y<=220;y+=50)svg+=poly([[-370,y,-2],[370,y,-2],[370,y+1,-2],[-370,y+1,-2]],'#d9e2d0','none');
 svg+=poly([[-365,-2,0],[365,-2,0],[365,26,0],[-365,26,0]],'#fcfbef','#d8dbc9');
 svg+=poly([[10,-235,0],[35,-235,0],[35,235,0],[10,235,0]],'#cadad6','none');
 const trees=[[-315,-150],[-320,10],[-160,170],[75,145],[320,-145],[335,130],[-100,-170],[85,-180]];
 for(const [x,y] of trees){const [px,py]=project(x,y,10);svg+=`<ellipse cx="${px}" cy="${py+8*scale}" rx="${14*scale}" ry="${6*scale}" fill="#819d6d22"/><circle cx="${px}" cy="${py}" r="${11*scale}" fill="#a8c092"/><circle cx="${px-3*scale}" cy="${py-4*scale}" r="${7*scale}" fill="#b9cea5"/>`;}
 const buildings=state.buildings.filter(b=>shapes[b.building_id]).sort((a,b)=>{const aa=shapes[a.building_id],bb=shapes[b.building_id];return (aa.x-bb.x)*Math.sin(angle)+(aa.y-bb.y)*Math.cos(angle);});
 let markers='';
 for(const building of buildings){
   const id=building.building_id,s=shapes[id],selected=id===state.building;
   if(focus&&!selected)continue;
   const locations=state.locations.filter(l=>l.building_id===id),levels=[...new Set(locations.map(r=>Number(r.floor)))].sort((a,b)=>a-b);
   const max=Math.max(1,...levels),expanded=!!focus;
   svg+=`<g class="model-building" tabindex="0" role="button" aria-label="Explore ${safe(building.name)}" data-model-building="${safe(id)}">`;
   svg+=box(s.x,s.y,s.w+14,s.d+14,0,4,['#d2d9bf','#b1bf9f','#9fab90']);
   for(let f=1;f<=max;f++){
     const top=expanded?f*15:f*8,active=String(state.floor)===String(f),mapped=levels.includes(f);
     const tones=active?['#e3d5a6','#bca46a','#a38a53']:mapped?['#eef0dc','#c4d0be','#a8bcae']:['#e5eadf','#d1dacd','#becdc0'];
     const opacity=expanded&&state.floor!=='all'&&!active?.22:1;
     svg+=`<g opacity="${opacity}" ${expanded&&mapped?`class="model-level" tabindex="0" role="button" aria-label="View Level ${f}" data-model-floor="${f}"`:''}>`;
     svg+=box(s.x,s.y,s.w,s.d,top,4,tones);
     if(!expanded){svg+=box(s.x,s.y,s.w-5,s.d-5,top+4,4,['#cbd7cd','#8ba79d','#739187']);}
     if(s.wings && !expanded)svg+=box(s.x-s.w*.35,s.y+s.d*.38,s.w*.3,s.d*.48,top,7,tones);
     if(expanded&&mapped){const [lx,ly]=project(s.x-s.w/2-12,s.y+s.d/2,top+4);svg+=`<text x="${lx}" y="${ly}" class="floor-label">L${f}</text>`;}
     svg+='</g>';
   }
   if(!expanded){
     const roof=max*8+8;
     svg+=box(s.x,s.y,s.w*.63,s.d*.6,roof,2,['#607b89','#4c6370','#435963']);
     for(let k=-2;k<=2;k++)svg+=poly([[s.x+k*s.w*.11-1,s.y-s.d*.3,roof+2.3],[s.x+k*s.w*.11+1,s.y-s.d*.3,roof+2.3],[s.x+k*s.w*.11+1,s.y+s.d*.3,roof+2.3],[s.x+k*s.w*.11-1,s.y+s.d*.3,roof+2.3]],'#9eafb8','none');
   }
   svg+='</g>';
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
 svg+=markers+`<text x="24" y="539" class="model-footnote">${focus?'Select a floor or a crowd marker':'CAMPUS WEST                                      CAMPUS EAST'}</text></svg>`;
 host.innerHTML=svg;
 const bind=(selector,fn)=>host.querySelectorAll(selector).forEach(el=>{const activate=e=>{e.stopPropagation();fn(el);};el.onclick=activate;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate(e);}};});
 bind('[data-model-building]',el=>{if(el.dataset.modelBuilding!==state.building)onBuilding(el.dataset.modelBuilding);});
 bind('[data-model-floor]',el=>onFloor(el.dataset.modelFloor));
 bind('[data-model-room]',el=>onRoom(el.dataset.modelRoom));
 const floors=focus?[...new Set(state.locations.filter(l=>l.building_id===state.building).map(l=>Number(l.floor)))].sort((a,b)=>a-b):[];
 document.getElementById('model-floors').innerHTML=focus?['all',...floors].map(f=>`<button data-model-select-floor="${f}" class="${String(state.floor)===String(f)?'active':''}" aria-pressed="${String(state.floor)===String(f)}">${f==='all'?'All levels':'Level '+f}</button>`).join(''):'<span>Choose E2, E6, W1, W3 or W5 to explore its floors.</span>';
 document.querySelectorAll('[data-model-select-floor]').forEach(el=>el.onclick=()=>onFloor(el.dataset.modelSelectFloor));
}
