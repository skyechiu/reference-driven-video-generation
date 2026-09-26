const {open}=require('./common.js');
const fs=require('fs');
const W=+process.env.W||1280,H=+process.env.H||720, OUT=process.env.OUT||'cap';
fs.mkdirSync(OUT,{recursive:true});
const helpers=fs.readFileSync('helpers.js','utf8');
(async()=>{const {b,p}=await open(W,H);
 await p.goto('https://activetheory.net/work',{waitUntil:'load',timeout:90000});
 await p.waitForTimeout(18000);
 await p.evaluate(helpers);
 for(let i=0;i<30;i++){const n=await p.evaluate(()=>__AT.cards().length);if(n>=14)break;await p.waitForTimeout(3000);}
 await p.mouse.move(W-5,H/2); // park mouse off cards
 const info=await p.evaluate(()=>{const s=AppState.get("ViewController/scroll");return {views:s.views.map(v=>({start:v.start,height:v.height,end:v.end})), N:__AT.cards().length}});
 fs.writeFileSync(`${OUT}/views.json`,JSON.stringify(info));
 console.log(JSON.stringify(info));
 const results={};
 const goto=async(k,frac=0)=>{await p.evaluate(([k,frac,N])=>{const s=AppState.get("ViewController/scroll");const wv=s.views[2];
     const p0=__AT.progressFor(k,N), p1=__AT.progressFor(Math.min(k+1,N-1),N); const prog=p0+(p1-p0)*frac;
     const H=Stage.height; const pos=wv.start+prog*(wv.height+H)-H; s.scrollTo(pos,0);},[k,frac,info.N]);
   // settle: wait until scrollProgress reaches target and camera stops
   const target=await p.evaluate(([k,frac,N])=>{const p0=__AT.progressFor(k,N), p1=__AT.progressFor(Math.min(k+1,N-1),N);return p0+(p1-p0)*frac;},[k,frac,info.N]);
   for(let i=0;i<60;i++){await p.waitForTimeout(1500);
     const st=await p.evaluate(async()=>{const a=__AT.cam().group.position.clone();const pr=AppState.get("Work/scrollProgress");await new Promise(r=>setTimeout(r,1500));return {mv:a.distanceTo(__AT.cam().group.position),pr}});
     if(Math.abs(st.pr-target)<0.0003&&st.mv<0.002){console.log('settled',k,frac,st.pr,target);break;}}
 };
 const shot=async(name)=>{await p.waitForTimeout(2500); await p.screenshot({path:`${OUT}/${name}.png`}); results[name]=await p.evaluate(()=>__AT.metrics()); console.log('shot',name,results[name].scrollProgress); fs.writeFileSync(`${OUT}/metrics_${process.env.K||6}.json`,JSON.stringify(results));};
 const K=+(process.env.K||6);
 const freeze=async()=>{await p.evaluate(()=>{if(!window.__tm){window.__tm=Render.createTimeMultiplier();} window.__tm.value=+(window.__FRZ||1e-4);}); await p.waitForTimeout(3000);};
 const unfreeze=async()=>{await p.evaluate(()=>{if(window.__tm) window.__tm.value=1;});};
 if(!process.env.ONLY_BETWEEN){ await goto(K,0); await freeze(); await shot(`c${K}_base`);
 // UI (text) off
 await p.evaluate(()=>__AT.cards().forEach(c=>c.ui.visible=false)); await shot(`c${K}_noUI`);
 await p.evaluate(()=>__AT.cards().forEach(c=>c.ui.visible=true));
 // bloom off
 await p.evaluate(()=>{const c=__AT.composite(); window.__bl=c.uniforms.tUnrealBloom.value; window.__ls=c.uniforms.tLightStreak.value; c.uniforms.tUnrealBloom.value=__AT.black();}); await shot(`c${K}_noBloom`);
 await p.evaluate(()=>{const c=__AT.composite(); c.uniforms.tLightStreak.value=__AT.black();}); await shot(`c${K}_noBloom_noStreak`);
 await p.evaluate(()=>__AT.cards().forEach(c=>c.ui.visible=false)); await shot(`c${K}_noBloom_noStreak_noUI`);
 await p.evaluate(()=>{__AT.cards().forEach(c=>c.ui.visible=true); const c=__AT.composite(); c.uniforms.tUnrealBloom.value=window.__bl; c.uniforms.tLightStreak.value=window.__ls;});
 // refraction off (glass only shows still/env)
 await p.evaluate(()=>__AT.cards().forEach(c=>__AT.force(c.pane.shader.uniforms.tRefraction,__AT.black()))); await shot(`c${K}_noRefraction`);
 await p.evaluate(()=>__AT.cards().forEach(c=>__AT.force(c.pane.shader.uniforms.tMap,__AT.black()))); await shot(`c${K}_noRefraction_noThumb`);
 await p.evaluate(()=>{const r=AppState.get("Work/refraction");__AT.cards().forEach(c=>{__AT.unforce(c.pane.shader.uniforms.tRefraction,r)});});
 await p.evaluate(()=>{window.__thumbs=[];}); // thumb stays black; restore by reload later
 // hover forcing on nearest card
 await p.reload({waitUntil:'load'}); await p.waitForTimeout(18000); await p.evaluate(helpers); for(let i=0;i<30;i++){const n=await p.evaluate(()=>__AT.cards().length);if(n>=14)break;await p.waitForTimeout(3000);} await p.mouse.move(W-5,H/2);
 await goto(K,0); await freeze();
 const nearest=async()=>p.evaluate(()=>{const m=__AT.metrics();return m.cards.reduce((a,c)=>c.distCam<a.distCam?c:a).i});
 const ni=await nearest();
 for(const hv of [0,0.25,0.5,0.75,1]){
   await p.evaluate(([ni,hv])=>{const c=__AT.cards()[ni];__AT.force(c.pane.shader.uniforms.uHover,hv);__AT.force(c.ui.shader.uniforms.uHover,hv);},[ni,hv]);
   await shot(`c${K}_hover${hv}`);
 }
 await p.evaluate(([ni])=>{const c=__AT.cards()[ni];__AT.unforce(c.pane.shader.uniforms.uHover,0);__AT.unforce(c.ui.shader.uniforms.uHover,0);},[ni]); await unfreeze();
 }
 // between cards
 for(const f of [0.25,0.5,0.75,1]){await unfreeze(); await goto(K,f); await freeze(); await shot(`c${K}_f${f}`);}
 fs.writeFileSync(`${OUT}/metrics_${K}.json`,JSON.stringify(results));
 await b.close();})().catch(e=>{console.error('ERR',e);process.exit(1)});
