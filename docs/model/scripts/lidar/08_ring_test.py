"""Ring (rim-around-hollow) score: for a center and radius R, count of 12 sectors where the rim annulus (|d-R|<0.75 m)
is >=3 cm above both the interior (d<R-1.5) and an outer annulus (R+1.5..R+3.5). Compare house-area hits
with a background sample of the open terrace 60-150 m from the house."""
import sys; sys.path.insert(0, sys.argv[1])
from common import *
G=load(); r=.5; x0=float(G['x0']); y1=float(G['y1']); dem=G['dem']; n=640
xs=x0+r*(np.arange(n)+.5); ys=y1-r*(np.arange(n)+.5); GX,GY=np.meshgrid(xs,ys)
def score(cx,cy,R):
    i=int((y1-cy)/r); j=int((cx-x0)/r); w=int((R+4)/r)+1
    if i-w<0 or j-w<0 or i+w>=n or j+w>=n: return -1
    sl=np.s_[i-w:i+w, j-w:j+w]; d=np.hypot(GX[sl]-cx,GY[sl]-cy); z=dem[sl]
    ang=np.arctan2(GY[sl]-cy,GX[sl]-cx); sec=((ang+np.pi)/(2*np.pi)*12).astype(int)%12
    rim=np.abs(d-R)<0.75; inn=d<R-1.5; out=(d>R+1.5)&(d<R+3.5); ok=0
    for s in range(12):
        a=rim&(sec==s); b=inn&(sec==s); c=out&(sec==s)
        if a.sum() and b.sum() and c.sum() and np.nanmean(z[a])>np.nanmean(z[b])+0.03 and np.nanmean(z[a])>np.nanmean(z[c])+0.03: ok+=1
    return ok
from scipy import ndimage as ndi
sm=ndi.gaussian_filter(np.nan_to_num(dem,nan=np.nanmean(dem)),10); gy,gx=np.gradient(sm,r); cs=np.degrees(np.arctan(np.hypot(gx,gy)))
rng=np.random.default_rng(1)
for Rs,label in (((3,3.5,4,4.5,5),'pit-with-spoil R3-5 m'),((7.5,9,10,11,12.5),'corral-size ring R7.5-12.5 m')):
    bg=[]
    while len(bg)<400:
        dx,dy=rng.uniform(-150,150,2); d=np.hypot(dx,dy)
        if d<60 or d>150: continue
        i=int((y1-HC[1]-dy)/r); j=int((HC[0]+dx-x0)/r)
        if not(0<=i<n and 0<=j<n) or cs[i,j]>3.5 or G['chm'][i,j]>3: continue
        s=max(score(HC[0]+dx,HC[1]+dy,R) for R in Rs)
        if s>=0: bg.append(s)
    bg=np.array(bg)
    print(label, 'background: frac>=8:',(bg>=8).mean(),' frac>=10:',(bg>=10).mean(), ' 99th pct',np.percentile(bg,99))
print('D2 pit (-16,+2):', max(score(HC[0]-16,HC[1]+2,R) for R in (3,3.5,4)))

# exhaustive search with identical settings in house window vs two background windows of equal size
def search(dx0,dx1,dy0,dy1,Rs):
    hits=[]
    for dx in np.arange(dx0,dx1+0.1,1):
        for dy in np.arange(dy0,dy1+0.1,1):
            s=max(score(HC[0]+dx,HC[1]+dy,R) for R in Rs)
            if s>=8: hits.append((s,dx,dy))
    hits.sort(reverse=True); kept=[]
    for h in hits:
        if all(np.hypot(h[1]-k[1],h[2]-k[2])>=6 for k in kept): kept.append(h)
    return kept
for Rs,label in (((3,3.5,4,4.5,5),'R3-5'),((7.5,9,10,11,12.5),'R7.5-12.5')):
    for name,win in (('house',(-40,40,-40,60)),('west terrace bg',(-145,-65,-50,50)),('north-west bg',(-140,-60,55,140))):
        k=search(*win,Rs); print(label,name,len(k),k[:6])
