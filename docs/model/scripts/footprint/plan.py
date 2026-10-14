import numpy as np, json, sys
from PIL import Image, ImageDraw
import solve, crop
D=np.pi/180
def load(fn='solve_out.json'):
    x=np.array(json.load(open(fn))['x']); return solve.unpack(x)
def mosaic(P,th,h,tl,pans=(1,5,2),ext=(-8,18,-16,8),res=0.03,maxr=14):
    x0,x1,y0,y1=ext
    xs=np.arange(x0,x1,res); ys=np.arange(y1,y0,-res)
    X,Y=np.meshgrid(xs,ys)
    out=np.zeros(X.shape+(3,),np.uint8); best=np.full(X.shape,1e9)
    for p in pans:
        a=np.asarray(Image.open(f'../panos/{p}.jpg')); H,W=a.shape[:2]
        dx=X-P[p][0]; dy=Y-P[p][1]; r=np.hypot(dx,dy)
        bt=np.degrees(np.arctan2(dx,dy))
        bt_tag=bt-th[p]
        e=-np.degrees(np.arctan2(h[p],r))+tl[p][0]*np.cos(bt_tag*D)+tl[p][1]*np.sin(bt_tag*D)
        px=((((bt_tag-crop.HD[p])/360+0.5)%1)*W).astype(int)%W
        py=((0.5-e/180)*H).astype(int).clip(0,H-1)
        m=(r<best)&(r<maxr)&(r>0.6)
        out[m]=a[py[m],px[m]]; best[m]=r[m]
    return Image.fromarray(out),(x0,y1,res)
if __name__=='__main__':
    P,th,h,tl,S=load()
    im,(x0,y1,res)=mosaic(P,th,h,tl)
    d=ImageDraw.Draw(im)
    def toPix(x,y): return ((x-x0)/res,(y1-y)/res)
    for s,(x,y) in S.items():
        u,v=toPix(x,y); d.ellipse([u-6,v-6,u+6,v+6],outline=(255,0,0),width=2); d.text((u+8,v-8),s,fill=(255,255,0))
    for p in P:
        u,v=toPix(*P[p]); d.rectangle([u-5,v-5,u+5,v+5],outline=(0,255,255),width=2); d.text((u+8,v),f'P{p}',fill=(0,255,255))
    for gx in range(-8,19,2):
        u,_=toPix(gx,0); d.line([(u,0),(u,8)],fill='white'); d.text((u+2,10),str(gx),fill='white')
    for gy in range(-16,9,2):
        _,v=toPix(0,gy); d.line([(0,v),(8,v)],fill='white'); d.text((10,v-5),str(gy),fill='white')
    im.save('crops/plan_mosaic.jpg',quality=88); print(im.size)
