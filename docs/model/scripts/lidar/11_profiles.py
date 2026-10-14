"""Raw ground-point profiles through key candidates and the house-to-river bluff profile."""
import sys, json; sys.path.insert(0, sys.argv[1])
from common import *
P=np.load(D+'/dl/pts.npz'); g=P['cls']==2
C={c['label']:c for c in json.load(open(D+'/candidates.json'))['candidates']}
def sw(ax,cx,cy,az,L,w,title):
    a=np.radians(az); ux,uy=np.sin(a),np.cos(a); dx=P['E']-cx; dy=P['N']-cy
    al=dx*ux+dy*uy; ac=-dx*uy+dy*ux; m=(np.abs(ac)<w)&(np.abs(al)<=L)
    ax.scatter(al[m&g],P['z'][m&g],s=4,c='k',label='ground (class 2)')
    v=m&np.isin(P['cls'],[1]); ax.scatter(al[v],P['z'][v],s=3,c='g',alpha=.35,label='unclassified/veg (class 1)')
    w9=m&(P['cls']==9); ax.scatter(al[w9],P['z'][w9],s=3,c='b',alpha=.5,label='water (class 9)')
    lo=P['z'][m&g].min()-.2; hi=P['z'][m&g].max()+.6; ax.set_ylim(lo,hi)
    ax.set_title(title,fontsize=9); ax.grid(alpha=.3); ax.set_xlabel(f'distance along az {az:.0f}° (m)'); ax.set_ylabel('m NAVD88')
fig=plt.figure(figsize=(18,16)); gs=fig.add_gridspec(4,2)
ax=fig.add_subplot(gs[0,:]); sw(ax,HC[0],HC[1],101.7,170,1.0,'House center -> river, az 101.7° (perpendicular to house long axis), 2 m swath. 0 = house center')
ax.set_xlim(-30,170); ax.axvspan(-4.6,4.6,color='y',alpha=.25,label='house footprint'); ax.legend(fontsize=7,loc='upper right')
ax.annotate('terrace edge / "low bluff": ~2.0 m drop between 20 and 48 m E',xy=(35,647.9),xytext=(40,649.4),arrowprops=dict(arrowstyle='->'),fontsize=8)
ax.annotate('modern cut bank ~1 m, water 643.65 m (Nov 2021)',xy=(142,644.4),xytext=(95,646.6),arrowprops=dict(arrowstyle='->'),fontsize=8)
items=[('D1',90,'D1 W-E (house NW corner)'),('D1',11.7,'D1 S-N along house axis'),('D2',90,'D2 W-E (round pit W of house)'),('D2',0,'D2 S-N'),('D13',90,'D13 W-E (50 m NNW)'),('D3',0,'D3 S-N (19 m N; rise to knoll at right)')]
for k,(lab,az,t) in enumerate(items):
    a=fig.add_subplot(gs[1+k//2,k%2]); c=C[lab]; sw(a,c['E'],c['N'],az,12,0.75,t+' — 1.5 m swath, 0 = candidate centroid'); a.axvline(0,color='r',lw=.5)
    if k==0: a.legend(fontsize=7)
plt.tight_layout(); plt.savefig(D+'/images/profiles_raw_points.jpg',dpi=90)
