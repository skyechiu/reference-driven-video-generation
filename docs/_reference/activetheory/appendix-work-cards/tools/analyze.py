import json, sys, numpy as np
from PIL import Image, ImageDraw
D=sys.argv[1]; K=sys.argv[2]
M=json.load(open(f'{D}/metrics_{K}.json'))
def img(n): return np.asarray(Image.open(f'{D}/c{K}_{n}.png').convert('RGB')).astype(np.float32)
def luma(a): return a[...,0]*0.299+a[...,1]*0.587+a[...,2]*0.114
def poly_mask(corners, shape, shrink=0.0):
    c=np.array([[x,y] for x,y,z in corners]); ctr=c.mean(0); c=ctr+(c-ctr)*(1-shrink)
    im=Image.new('L',(shape[1],shape[0]),0); ImageDraw.Draw(im).polygon([tuple(p) for p in c],fill=1)
    return np.asarray(im).astype(bool)
base=img('base'); H,W=base.shape[:2]
m=M[f'c{K}_base']; cards=sorted(m['cards'],key=lambda c:c['distCam'])
out={'stage':[W,H]}
rows=[]
for c in cards:
    xs=[p[0] for p in c['corners']]; ys=[p[1] for p in c['corners']]
    x0,x1,y0,y1=max(0,min(xs)),min(W,max(xs)),max(0,min(ys)),min(H,max(ys))
    vis_area=max(0,x1-x0)*max(0,y1-y0)
    mk=poly_mask(c['corners'],base.shape,0.08)
    L=luma(base)[mk] if mk.any() else np.array([np.nan])
    rows.append(dict(i=c['i'],distCam=c['distCam'],facing=c['facingDeg'],ro=c['renderOrder'],bbox=[round(x0),round(y0),round(x1),round(y1)],
        screenW=round((max(xs)-min(xs))/W*100,1),screenH=round((max(ys)-min(ys))/H*100,1),visibleArea=round(vis_area/(W*H)*100,1),
        meanLuma=round(float(np.nanmean(L)),1), p95=round(float(np.nanpercentile(L,95)),1) if mk.any() else None))
out['cards']=rows
center=cards[0]; mk=poly_mask(center['corners'],base.shape,0.04)
def region_stats(a,mask): L=luma(a)[mask]; return dict(mean=round(float(L.mean()),2), rgb=[round(float(a[...,k][mask].mean()),1) for k in range(3)])
states=['base','noUI','noBloom','noBloom_noStreak','noBloom_noStreak_noUI','noRefraction','noRefraction_noThumb','hover0','hover0.25','hover0.5','hover0.75','hover1']
S={}
for s in states:
    try: a=img(s)
    except Exception as e: continue
    S[s]=a
out['centerCard']={s:region_stats(S[s],mk) for s in S}
out['frame']={s:round(float(luma(S[s]).mean()),2) for s in S}
# text = base - noUI (additive UI)
t=S['base']-S['noUI']; tl=luma(t)
tm=(tl>25)&mk
ys,xs=np.where(tm)
out['text']=dict(pixels=int(tm.sum()), bbox=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())] if len(xs) else None,
  addMeanRGB=[round(float(t[...,k][tm].mean()),1) for k in range(3)], addP95=round(float(np.percentile(tl[tm],95)),1),
  finalMeanRGB=[round(float(S['base'][...,k][tm].mean()),1) for k in range(3)], finalP95=round(float(np.percentile(luma(S['base'])[tm],95)),1),
  finalMax=round(float(luma(S['base'])[tm].max()),1),
  underTextBgRGB=[round(float(S['noUI'][...,k][tm].mean()),1) for k in range(3)])
# RGB shift: horizontal cross-corr of R vs B on text-add image within bbox
if len(xs):
    x0,y0,x1,y1=out['text']['bbox']; R=t[y0:y1+1,x0:x1+1,0]; B=t[y0:y1+1,x0:x1+1,2]; G=t[y0:y1+1,x0:x1+1,1]
    def best(a,b):
        best=None
        for dx in range(-6,7):
            for dy in range(-3,4):
                sa=np.roll(np.roll(a,dx,1),dy,0); v=float((sa*b).sum())
                if best is None or v>best[0]: best=(v,dx,dy)
        return best[1:]
    out['text']['shift_R_to_G']=best(R,G); out['text']['shift_B_to_G']=best(B,G)
    # stroke width: horizontal runs in text mask
    runs=[]
    for row in tm[y0:y1+1,x0:x1+1]:
        r=0
        for v in row:
            if v: r+=1
            elif r: runs.append(r); r=0
    runs=np.array(runs); out['text']['hRunMedian']=float(np.median(runs)) if len(runs) else None
    out['text']['heightPxOfCard']=round((y1-y0)/ (max(p[1] for p in center['corners'])-min(p[1] for p in center['corners']))*100,1)
    out['text']['widthPctOfCard']=round((x1-x0)/ (max(p[0] for p in center['corners'])-min(p[0] for p in center['corners']))*100,1)
# bloom contribution
b=S['base']-S['noBloom']; out['bloom']=dict(frameMean=round(float(luma(b).mean()),2), cardMean=round(float(luma(b)[mk].mean()),2), textMean=round(float(luma(b)[tm].mean()),2) if tm.any() else None,
   pctOfCard=round(float(luma(b)[mk].mean()/luma(S['base'])[mk].mean()*100),1), pctOfText=round(float(luma(b)[tm].mean()/luma(S['base'])[tm].mean()*100),1))
if 'noBloom_noStreak' in S:
    st=S['noBloom']-S['noBloom_noStreak']; out['streak']=dict(frameMean=round(float(luma(st).mean()),2), cardMean=round(float(luma(st)[mk].mean()),2))
if 'noBloom_noStreak_noUI' in S:
    bt=(S['base']-S['noUI'])-(S['noBloom_noStreak']-S['noBloom_noStreak_noUI'])
    out['textGlowFromBloom']=dict(halo_mean_outside_text=round(float(luma(bt)[mk&~tm].mean()),3))
json.dump(out,open(f'{D}/analysis_{K}.json','w'),indent=1)
print(json.dumps(out,indent=1))
