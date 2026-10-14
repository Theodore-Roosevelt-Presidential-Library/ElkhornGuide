import sys
from PIL import Image, ImageDraw
S='/tmp/claude-0/-home-claude/4cec2ed1-e3f9-5b51-a27d-73f13cf5ade5/scratchpad/'
HD={1:132,2:120,3:101,4:172,5:64,6:316,7:50}
W,H=4608,2304
def crop(p,b0,b1,e0,e1,scale=1.0,step=5,out=None):
    im=Image.open(S+f'panos/{p}.jpg')
    hd=HD[p]
    x0=((b0-hd)/360+0.5)*W; x1=((b1-hd)/360+0.5)*W
    y0=(0.5-e0/180)*H; y1=(0.5-e1/180)*H
    # handle wrap
    x0i=int(round(x0)); x1i=int(round(x1))
    import numpy as np
    a=np.asarray(im)
    cols=[(x% W) for x in range(x0i,x1i)]
    sub=a[int(y0):int(y1)][:,cols]
    c=Image.fromarray(sub)
    d=ImageDraw.Draw(c)
    b=int(np.ceil(b0/step)*step)
    while b<=b1:
        x=((b-hd)/360+0.5)*W-x0i
        d.line([(x,0),(x,12)],fill=(255,0,0),width=2); d.line([(x,c.height-12),(x,c.height)],fill=(255,0,0),width=2)
        d.text((x+2,12),str(b%360),fill=(255,255,0))
        b+=step
    e=int(np.floor(e0/step)*step)
    while e>=e1:
        y=(0.5-e/180)*H-int(y0)
        d.line([(0,y),(12,y)],fill=(0,255,255),width=2); d.line([(c.width-12,y),(c.width,y)],fill=(0,255,255),width=2)
        d.text((14,y-5),str(e),fill=(0,255,255))
        e-=step
    if scale!=1: c=c.resize((int(c.width*scale),int(c.height*scale)),Image.LANCZOS)
    c.save(out or S+f'footprint/crops/p{p}_{b0}_{b1}_{e0}_{e1}.jpg',quality=88)
    print(out or S+f'footprint/crops/p{p}_{b0}_{b1}_{e0}_{e1}.jpg', c.size)
if __name__=='__main__':
    a=sys.argv[1:]
    crop(int(a[0]),float(a[1]),float(a[2]),float(a[3]),float(a[4]),float(a[5]) if len(a)>5 else 1.0, int(a[6]) if len(a)>6 else 5)
