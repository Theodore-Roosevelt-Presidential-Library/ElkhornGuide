"""100 m and 300 m ground-DEM contour maps (10 cm / 25 cm) over hillshade, with candidates."""
import sys, json; sys.path.insert(0, sys.argv[1])
from common import *
G=load(); ext=G['extent']; V=dict(np.load(D+'/derivs.npz'))
C=[dict(c,id=c['label']) for c in json.load(open(D+'/candidates.json'))['candidates'] if c['tier'] in 'AB']
r=.5; x0=float(G['x0']); y1=float(G['y1']); n=640
xs=x0+r*(np.arange(n)+.5); ys=y1-r*(np.arange(n)+.5)
for half,iv,name in ((50,0.1,'zoom100m_contours10cm.jpg'),(150,0.25,'overview300m_contours25cm.jpg')):
    fig,ax=plt.subplots(figsize=(11,11))
    ax.imshow(G['dem'],cmap='terrain',vmin=643.5,vmax=650,extent=ext,alpha=.6)
    ax.imshow(V['hs315'],cmap='gray',vmin=.2,vmax=1,extent=ext,alpha=.4)
    cs=ax.contour(xs,ys,G['dem'],levels=np.arange(643,651,iv),colors='k',linewidths=0.35)
    cs2=ax.contour(xs,ys,G['dem'],levels=np.arange(643,651,1.0),colors='k',linewidths=1.0)
    ax.clabel(cs2,fmt='%.0f',fontsize=7)
    decorate(ax,half,cands=[c for c in C if c['dist_m']<=half*1.4],grid=10 if half<100 else 25,label_size=8)
    ax.set_title(f'Ground DEM (m NAVD88) with {int(iv*100)} cm contours (bold = 1 m) — {2*half} m view',fontsize=10)
    plt.tight_layout(); plt.savefig(D+'/images/'+name,dpi=100); plt.close()
