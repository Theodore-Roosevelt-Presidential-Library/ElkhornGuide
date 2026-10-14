"""Contour close-ups (5 cm interval) on the 0.5 m TIN DEM with ground points, for key candidates."""
import sys, json; sys.path.insert(0, sys.argv[1])
from common import *
import matplotlib.patheffects as pe
G=load(); ext=G['extent']; V=dict(np.load(D+'/derivs.npz'))
P=np.load(D+'/dl/pts.npz'); g=P['cls']==2
C={c['label']:c for c in json.load(open(D+'/candidates.json'))['candidates']}
r=.5; x0=float(G['x0']); y1=float(G['y1']); n=640
xs=x0+r*(np.arange(n)+.5); ys=y1-r*(np.arange(n)+.5)
views=[('D10_scarp_NNE',(C['D10']['E'],C['D10']['N']),9),('D12_L1_NNE',(C['D12']['E'],C['D12']['N']),10),('D7_scarp_SE',(C['D7']['E'],C['D7']['N']),8),
       ('D9_SSE',(C['D9']['E'],C['D9']['N']),8),('D8_D5_NW',((C['D8']['E']+C['D5']['E'])/2,(C['D8']['N']+C['D5']['N'])/2),10),
       ('D6_S',(C['D6']['E'],C['D6']['N']),8)]
fig,axs=plt.subplots(2,3,figsize=(21,14))
for ax,(nm,(cx,cy),h) in zip(axs.ravel(),views):
    ax.imshow(V['lrm5'],cmap='RdBu_r',vmin=-.25,vmax=.25,extent=ext,interpolation='nearest')
    cs=ax.contour(xs,ys,G['dem'],levels=np.arange(643,651,0.05),colors='k',linewidths=0.4)
    m=g&(np.abs(P['E']-cx)<h)&(np.abs(P['N']-cy)<h)
    ax.plot(P['E'][m],P['N'][m],'.',ms=1,color='0.3')
    decorate(ax,h,cands=[dict(c,id=k) for k,c in C.items() if c['tier'] in 'AB'],grid=5 if h>8 else 2,label_size=11,center=(cx,cy))
    ax.set_title(f'{nm}: LRM-5 m colour, 5 cm contours, ground points (dots)',fontsize=10)
plt.tight_layout(); plt.savefig(D+'/images/closeups_contours_2.jpg',dpi=80)
