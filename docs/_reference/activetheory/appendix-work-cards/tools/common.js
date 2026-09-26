const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const SPOOF = `(()=>{for(const C of [WebGLRenderingContext,WebGL2RenderingContext]){const g=C.prototype.getParameter;C.prototype.getParameter=function(p){if(p===0x9246)return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)';if(p===0x9245)return 'Google Inc. (NVIDIA)';return g.call(this,p)}}})();`;
async function open(w=1280,h=720){
 const b = await chromium.launch({executablePath:'/opt/pw-browsers/chromium', proxy:{server:'http://127.0.0.1:34107'},
   args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required']});
 const ctx = await b.newContext({viewport:{width:w,height:h},deviceScaleFactor:1,userAgent:'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'});
 await ctx.addInitScript(SPOOF);
 const p = await ctx.newPage();
 p.on('console',m=>{const t=m.text(); if(!/GPU stall|WebGL/.test(t)) console.log('CONSOLE',t.slice(0,200))});
 p.on('pageerror',e=>console.log('PAGEERR',e.message.slice(0,200)));
 return {b,p};
}
module.exports={open};
