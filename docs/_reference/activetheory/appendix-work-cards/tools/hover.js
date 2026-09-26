// Real-mouse hover test: does uHover respond, and the lerp curve vs wall-clock (frame-rate normalized).
const {open}=require('./common.js');const fs=require('fs');
const W=1280,H=720;
(async()=>{const {b,p}=await open(W,H);
 await p.goto('https://activetheory.net/work',{waitUntil:'load',timeout:90000});
 await p.waitForTimeout(18000); await p.evaluate(fs.readFileSync('helpers.js','utf8'));
 for(let i=0;i<30;i++){if(await p.evaluate(()=>__AT.cards().length)>=14)break;await p.waitForTimeout(3000);}
 await p.evaluate(()=>{const s=AppState.get("ViewController/scroll");const wv=s.views[2];const pr=__AT.progressFor(6,14);s.scrollTo(wv.start+pr*(wv.height+Stage.height)-Stage.height,0);});
 await p.waitForTimeout(15000);
 const info=await p.evaluate(()=>{const m=__AT.metrics();const c=m.cards.reduce((a,c)=>c.distCam<a.distCam?c:a);return {i:c.i,corners:c.corners}});
 const idx=await p.evaluate((i)=>__AT.cards().findIndex(c=>__AT.metrics().cards.find(x=>x.i===i)) ,info.i);
 const cx=info.corners.reduce((a,c)=>a+c[0],0)/4, cy=info.corners.reduce((a,c)=>a+c[1],0)/4;
 console.log('center',cx,cy,info.i);
 await p.evaluate((i)=>{window.__s=[];const t0=performance.now();window.__t0=t0;(function f(){const c=__AT.cards()[i];window.__s.push([performance.now()-t0,c.pane.shader.uniforms.uHover.value,Mouse.x,Mouse.y]);requestAnimationFrame(f)})()},info.i);
 for(let j=0;j<8;j++){await p.mouse.move(cx-40+j*10,cy+j*3,{steps:2});await p.waitForTimeout(800);}
 const tIn=await p.evaluate(()=>performance.now()-__t0);
 await p.waitForTimeout(12000);
 await p.screenshot({path:'hover_real_in.png'});
 await p.mouse.move(W-10,40,{steps:3});
 const tOut=await p.evaluate(()=>performance.now()-__t0);
 await p.waitForTimeout(12000);
 await p.screenshot({path:'hover_real_out.png'});
 const s=await p.evaluate(()=>window.__s);
 fs.writeFileSync('hover_samples.json',JSON.stringify({tIn,tOut,s}));
 console.log('tIn',tIn,'tOut',tOut,'n',s.length, JSON.stringify(s.filter((_,k)=>k%1==0).map(x=>[Math.round(x[0]),+x[1].toFixed(3),Math.round(x[2]),Math.round(x[3])])));
 await b.close();})();
