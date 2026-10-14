"""Trace the east scarp (steepest step between house terrace and swale) row by row and look for re-entrant notches
(dugout cut into bank). For each northing (0.5 m rows) within +-60 m of house, find the easting where the DEM first
drops below 647.8 m going east from the house terrace, then flag local westward re-entrants > 1.5 m deep and 2-8 m wide."""
import sys; sys.path.insert(0, sys.argv[1])
from common import *
from scipy import ndimage as ndi
G=load(); dem=G['dem']; r=.5; x0=float(G['x0']); y1=float(G['y1']); n=640
rows=[]; 
for dy in np.arange(-60,60.01,0.5):
    i=int((y1-(HC[1]+dy))/r); j0=int((HC[0]-x0)/r)
    prof=dem[i,j0:j0+int(80/r)]
    k=np.where(prof<647.8)[0]
    rows.append((dy, k[0]*r if len(k) else np.nan))
rows=np.array(rows); e=rows[:,1]
base=ndi.median_filter(np.nan_to_num(e,nan=np.nanmedian(e)),size=31)  # 15 m running median
dev=base-e  # positive = contour pulled west (re-entrant)
print('scarp (647.8 m contour) east of house center: median %.1f m, range %.1f-%.1f m'%(np.nanmedian(e),np.nanmin(e),np.nanmax(e)))
lab,nl=ndi.label(dev>1.5)
for k in range(1,nl+1):
    idx=np.where(lab==k)[0]; w=len(idx)*r
    print('re-entrant at dy %.1f..%.1f m, width %.1f m, max depth %.1f m'%(rows[idx[0],0],rows[idx[-1],0],w,dev[idx].max()))
fig,ax=plt.subplots(figsize=(6,8)); ax.plot(e,rows[:,0],'k',label='647.8 m contour'); ax.plot(base,rows[:,0],'r--',label='15 m running median')
ax.set_xlabel('m east of house center'); ax.set_ylabel('m north of house center'); ax.legend(); ax.grid(alpha=.3); ax.set_title('East scarp trace: re-entrants = possible dugout notches')
plt.tight_layout(); plt.savefig(D+'/images/scarp_trace.jpg',dpi=90)
# scarp height and steepest slope near house (dy -10..+10)
V=dict(np.load(D+'/derivs.npz'))
i0=int((y1-HC[1])/r); j0=int((HC[0]-x0)/r)
win=V['slope'][i0-20:i0+20, j0+30:j0+100]; print('max slope on scarp within +-10 m N/S of house: %.1f deg; 95th pct %.1f'%(win.max(),np.percentile(win,95)))
