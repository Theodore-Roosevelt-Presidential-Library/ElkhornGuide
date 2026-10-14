import numpy as np, math, json
from scipy.optimize import least_squares
d=np.load('terrain/terrain.npz'); meta=json.load(open('terrain/terrain_meta.json'))
xs,ys,Z=d['far_xs'],d['far_ys'],d['far_Z']; X,Y=np.meshgrid(xs,ys)
W=2467; cx=W/2; zc=-6.5
house=[((15,-4),1790),((15,62),2120)]
sky=[(467,557),(620,619),(870,644),(1100,594),(1415,545),(1650,619),(1808,644)]
def skyline_el(E,N,yaw,f,cols):
    b=np.degrees(np.arctan2(X-E,Y-N)); dist=np.hypot(X-E,Y-N); el=np.degrees(np.arctan2(Z-zc,dist))
    rel=((b-yaw+180)%360)-180; ok=(dist>350)&(np.abs(rel)<75)
    xi=cx+f*np.tan(np.radians(rel[ok])); e=el[ok]
    out=[]
    for c in cols:
        m=np.abs(xi-c)<6; out.append(e[m].max() if m.any() else 0.0)
    return np.array(out)
def res(p):
    E,N,yaw,f,y0=p
    r=[]
    for c,x in house:
        b=math.degrees(math.atan2(c[0]-E,c[1]-N)); r.append((cx+f*math.tan(math.radians(b-yaw))-x)/5)
    el=skyline_el(E,N,yaw,f,[s[0] for s in sky])
    for (sx,sy),e in zip(sky,el):
        r.append(((y0-f*math.tan(math.radians(e)))-sy)/10)
    return r
best=None
for dist in (300,450,600,800):
  for brg in (85,100,115):
    E=15+dist*math.sin(math.radians(brg));N=30+dist*math.cos(math.radians(brg))
    for f in (1300,2000,3000):
      r=least_squares(res,[E,N,(brg+180)%360,f,920],diff_step=1e-3)
      if best is None or r.cost<best.cost: best=r
p=best.x;E,N,yaw,f,y0=p
print('E N',round(E),round(N),'yaw',round(yaw%360,1),'f',round(f),'hfov',round(2*math.degrees(math.atan(cx/f)),1),'y0',round(y0),'cost',round(best.cost,1))
print('dist',round(math.hypot(E-15,N-30)),'brg',round(math.degrees(math.atan2(E-15,N-30))%360,1))
for c in ((165.4,-255.2),(133.3,-225.1)):
    b=math.degrees(math.atan2(c[0]-E,c[1]-N)); print('pred x',c,round(cx+f*math.tan(math.radians(b-yaw))))
print(np.round(res(p),1))
json.dump(dict(E=E,N=N,z=zc,yaw=yaw%360,f=f,hfov=2*math.degrees(math.atan(cx/f)),y0=y0,W=W),open('spec/river_camera_solve.json','w'),indent=1)
