"""Contour close-ups (5 cm interval) on the 0.5 m TIN DEM with ground points, for key candidates."""
import sys, json; sys.path.insert(0, sys.argv[1])
from common import *
import matplotlib.patheffects as pe
G=load(); ext=G['extent']; V=dict(np.load(D+'/derivs.npz'))
P=np.load(D+'/dl/pts.npz'); g=P['cls']==2
C={c['label']:c for c in json.load(open(D+'/candidates.json'))['candidates']}
r=.5; x0=float(G['x0']); y1=float(G['y1']); n=640
xs=x0+r*(np.arange(n)+.5); ys=y1-r*(np.arange(n)+.5)
views=[('house_D1_M1',HC,14),('D2_pit_west',(C['D2']['E'],C['D2']['N']),8),('D3_north',(C['D3']['E'],C['D3']['N']),10),
       ('D4_M4_southeast',((C['D4']['E']+C['M4']['E'])/2,(C['D4']['N']+C['M4']['N'])/2),10),('D13_nnw',(C['D13']['E'],C['D13']['N']),10),
       ('M2_M3_west',((C['M2']['E']+C['M3']['E'])/2,(C['M2']['N']+C['M3']['N'])/2),10)]
fig,axs=plt.subplots(2,3,figsize=(21,14))
for ax,(nm,(cx,cy),h) in zip(axs.ravel(),views):
    ax.imshow(V['lrm5'],cmap='RdBu_r',vmin=-.25,vmax=.25,extent=ext,interpolation='nearest')
    cs=ax.contour(xs,ys,G['dem'],levels=np.arange(643,651,0.05),colors='k',linewidths=0.4)
    m=g&(np.abs(P['E']-cx)<h)&(np.abs(P['N']-cy)<h)
    ax.plot(P['E'][m],P['N'][m],'.',ms=1,color='0.3')
    decorate(ax,h,cands=[dict(c,id=k) for k,c in C.items() if c['tier'] in 'AB'],grid=5 if h>8 else 2,label_size=11,center=(cx,cy))
    ax.set_title(f'{nm}: LRM-5 m colour, 5 cm contours, ground points (dots)',fontsize=10)
plt.tight_layout(); plt.savefig(D+'/images/closeups_contours.jpg',dpi=80)
