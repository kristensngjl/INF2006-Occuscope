import test from 'node:test';
import assert from 'node:assert/strict';
import {bindModelGestures} from '../model.js';

test('gestures preserve clicks, suppress drag clicks, capture pointers and intercept wheel',()=>{
 const handlers={},frames=[]; let redraws=0,captured=false;
 const old=globalThis.requestAnimationFrame;
 globalThis.requestAnimationFrame=fn=>{frames.push(fn);return frames.length;};
 const host={addEventListener:(name,fn)=>handlers[name]=fn,classList:{add(){},remove(){}},setPointerCapture(){captured=true;},hasPointerCapture(){return captured;},releasePointerCapture(){captured=false;},clientHeight:570};
 try{
  bindModelGestures(host,()=>redraws++);
  const event=(x,y)=>({button:0,pointerId:1,clientX:x,clientY:y,preventDefault(){}});
  handlers.pointerdown(event(10,10));handlers.pointermove(event(12,12));handlers.pointerup(event(12,12));
  let stopped=false;const click={preventDefault(){},stopImmediatePropagation(){stopped=true;}};
  handlers.click(click);assert.equal(stopped,false);assert.equal(frames.length,0);
  handlers.pointerdown(event(10,10));handlers.pointermove(event(80,25));assert.equal(captured,true);
  handlers.pointermove(event(90,30));assert.equal(frames.length,1);
  handlers.pointerup(event(90,30));assert.equal(captured,false);
  handlers.click(click);assert.equal(stopped,true);frames.shift()();assert.equal(redraws,1);
  let prevented=false;
  handlers.wheel({deltaY:80,deltaMode:0,ctrlKey:false,preventDefault(){prevented=true;}});
  assert.equal(prevented,true);frames.shift()();assert.equal(redraws,2);
  handlers.pointerdown(event(10,10));handlers.pointermove(event(40,20));handlers.pointercancel(event(40,20));assert.equal(captured,false);
 }finally{globalThis.requestAnimationFrame=old;}
});
