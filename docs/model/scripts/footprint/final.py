import numpy as np, json, math
from scipy.optimize import least_squares
from PIL import Image, ImageDraw
import solve, fit, crop
D=np.pi/180
L0,W0=18.29,9.14
GPS={1:(47.242072,-103.622272),2:(47.242072,-103.622275),3:(47.242117,-103.622122),4:(47.242561,-103.622617),
     5:(47.241881,-103.622194),6:(47.241669,-103.622011),7:(47.241283,-103.621981)}
NPS=(47.241898,-103.622276)
lat0,lon0=GPS[1]
mN=111132.9-559.8*math.cos(2*lat0*D); mE=111412.8*math.cos(lat0*D)
def ll2en(la,lo): return np.array([(lo-lon0)*mE,(la-lat0)*mN])
def en2ll(e,n,off): return (lat0+(n+off[1])/mN, lon0+(e+off[0])/mE)

# 1. registration (nominal priors) + line fit
x,(P,th,h,tl,S)=fit.run(1.5,0.0,1.0)
f=fit.fit_lines(S)
sc=W0/f['width']             # scale so the two stone rows are 9.14 m apart  => camera height ~1.36 m
P={k:np.array(v)*sc for k,v in P.items()}; S={k:np.array(v)*sc for k,v in S.items()}; h={k:v*sc for k,v in h.items()}
# 2. fixed-size rectangle fit: west edge F,G,H,A ; east edge J,L,K ; north edge A,M
WEST=['F','G','H','A']; EAST=['J','L','K']; NORTH=['A','M']
def rect(cx,cy,az,L=L0,W=W0):
    u=np.array([math.sin(az*D),math.cos(az*D)]); n=np.array([math.cos(az*D),-math.sin(az*D)])
    c=np.array([cx,cy])
    return [c-u*L/2-n*W/2, c+u*L/2-n*W/2, c+u*L/2+n*W/2, c-u*L/2+n*W/2]  # SW,NW,NE,SE
def rres(p,anchor_north=True,L=L0,W=W0):
    cx,cy,az=p[:3]
    u=np.array([math.sin(az*D),math.cos(az*D)]); n=np.array([math.cos(az*D),-math.sin(az*D)]); c=np.array([cx,cy])
    r=[(n@(S[s]-c)+W/2) for s in WEST]+[(n@(S[s]-c)-W/2) for s in EAST]
    if anchor_north: r+=[(u@(S[s]-c)-L/2) for s in NORTH]
    else:
        al=[u@(S[s]-c) for s in WEST+EAST+NORTH]; r+=[0.3*(max(al)+min(al))]  # centre stones along axis
    return r
sols={}
for name,an in [('north_anchored',True),('centred',False)]:
    s0=least_squares(lambda p: rres(p,an),[3,-4,12])
    sols[name]=dict(cx=s0.x[0],cy=s0.x[1],az=s0.x[2]%360,res=np.array(s0.fun),corners=rect(*s0.x))
# free-size fit (both rows + north anchor), length unconstrained => only report width
s1=least_squares(lambda p: rres(p[:3],True,L=L0,W=p[3]),[3,-4,12,9.1])
primary=sols['north_anchored']

# 3. georeference: robust offset from panos with fresh fixes and registered positions (1,5); pano 2 fix is stale (3 min old)
offs={p:ll2en(*GPS[p])-P[p] for p in (1,5)}
off=np.mean([offs[1],offs[5]],axis=0); spread=np.linalg.norm(offs[1]-offs[5])/2
# unregistered panos: place by GPS in local frame
Pall=dict(P)
for p in (3,4,6,7): Pall[p]=ll2en(*GPS[p])-off
thall=dict(th); hall=dict(h); tlall=dict(tl)
for p in (3,4,6,7): thall[p]=0.0; hall[p]=1.36; tlall[p]=(0.,0.)
nps_local=ll2en(*NPS)-off

# 4. results.json
def pt(e,n): la,lo=en2ll(e,n,off); return dict(E=round(float(e),2),N=round(float(n),2),lat=round(la,7),lon=round(lo,7))
names=['SW','NW','NE','SE']
res=dict(
 frame="Local ENU metres, origin = pano 1 camera position, +E east, +N true north. Lat/lon via offset estimated from fresh GPS fixes of panos 1 and 5 (absolute accuracy ~+-12 m).",
 scale_note=f"Range scale set so the two stone rows are 9.14 m apart (implied camera height {np.mean(list(h.values())):.2f} m; with a 1.50 m prior the rows are {f['width']:.2f} m apart).",
 heading_note="GPano PoseHeadingDegrees used as TRUE heading; relative headings of panos 1/2/5 agree within ~1 deg on the butte summit to the WNW; sun check agrees within ~3 deg, magnetic (~7 deg E decl.) would show a systematic offset. No PosePitch/PoseRoll tags present.",
 gps_offset_m=dict(E=round(float(off[0]),2),N=round(float(off[1]),2),half_disagreement_p1_vs_p5_m=round(float(spread),1)),
 panos={str(p):dict(registered=p in P, E=round(float(Pall[p][0]),2),N=round(float(Pall[p][1]),2),
        heading_correction_deg=round(float(thall[p]),2), cam_height_m=round(float(hall[p]),2),
        tilt_deg=[round(float(t),2) for t in tlall[p]], gps_raw=GPS[p]) for p in range(1,8)},
 stones={k:dict(**pt(*v), across_from_west_row_m=round(float(f['across'][k]*sc),2), along_axis_m=round(float(f['along'][k]*sc),2)) for k,v in S.items()},
 row_fit=dict(long_axis_azimuth_deg_true=round(float(f['az']),1), row_spacing_m_unscaled=round(float(f['width']),2), line_rms_m=round(float(f['rms']*sc),2),
     azimuth_sensitivity_deg="8.8-15.1 over heading prior +-3 deg and tilt prior; dominated by absolute heading"),
 rectangle_primary=dict(model="18.29 x 9.14 m, west row F-G-H-A, east row J-L-K, north wall through A and M (house extends south of the last visible stones)",
     long_axis_azimuth_deg_true=round(float(primary['az']),1), center=pt(primary['cx'],primary['cy']),
     corners={nm:pt(*c) for nm,c in zip(names,primary['corners'])}, edge_residuals_m=[round(float(v),2) for v in primary['res']],
     porch_side="east (long side facing +n, i.e. azimuth %.0f deg)"%((primary['az']+90)%360)),
 rectangle_alternative_centred=dict(model="same size, centred on the stone rows along the axis (both end walls unmarked)",
     long_axis_azimuth_deg_true=round(float(sols['centred']['az']),1), center=pt(sols['centred']['cx'],sols['centred']['cy']),
     corners={nm:pt(*c) for nm,c in zip(names,sols['centred']['corners'])}),
 free_width_fit_m=round(float(s1.x[3]),2),
 nps_cabin_site_stop_local=dict(E=round(float(nps_local[0]),1),N=round(float(nps_local[1]),1),
     dist_to_primary_center_m=round(float(np.hypot(*(nps_local-np.array([primary['cx'],primary['cy']])))),1)),
 uncertainty=dict(relative_position_m="~0.3-0.5 for stones seen from 2 panos, 1-3 for single-pano far stones (D, E, I)",
     azimuth_deg="+-3 (heading prior) ", absolute_m="+-12 (phone GPS)", length_placement="north-south placement of 18.3 m length is a hypothesis: only ~12-14 m of the rows is visible"))
json.dump(res,open('results.json','w'),indent=1)

# 5. top-down plot
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(9,11))
for nm,col,ls in [('north_anchored','tab:red','-'),('centred','tab:orange','--')]:
    c=np.array(sols[nm]['corners']+[sols[nm]['corners'][0]]); ax.plot(c[:,0],c[:,1],ls,color=col,lw=2,label=f'{nm} 18.3x9.1 m')
c=primary['corners']; ne,se=c[2],c[3]; nrm=np.array([math.cos(primary['az']*D),-math.sin(primary['az']*D)])
pc=np.array([se,ne,ne+nrm*2.4,se+nrm*2.4,se]); ax.plot(pc[:,0],pc[:,1],':',color='tab:red'); ax.text(*(ne+se)/2+nrm*1.2,'piazza\n(E side)',color='tab:red',ha='center',fontsize=8)
for k,v in S.items():
    seen=sum(1 for o in solve.OBS if o[1]==k)
    ax.plot(*v,'s',color='saddlebrown' if seen>1 else 'peru',ms=8); ax.annotate(k,v,xytext=(4,4),textcoords='offset points',fontweight='bold')
for p,v in Pall.items():
    ax.plot(*v,'o',color='tab:blue' if p in P else 'lightsteelblue',ms=9); ax.annotate(f'P{p}'+('' if p in P else ' (GPS only)'),v,xytext=(5,-12),textcoords='offset points',color='tab:blue')
ax.plot(*nps_local,'x',color='green',ms=10); ax.annotate('NPS "Cabin Site" stop',nps_local,xytext=(5,5),textcoords='offset points',color='green',fontsize=8)
ax.annotate('',xy=(-12,12),xytext=(-12,7),arrowprops=dict(arrowstyle='->',lw=2)); ax.text(-12,12.5,'N (true)',ha='center')
ax.plot([-12,-7],[-30,-30],'k',lw=3); ax.text(-9.5,-29.3,'5 m',ha='center')
ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_xlabel('East (m, from P1)'); ax.set_ylabel('North (m)')
ax.set_xlim(-15,30); ax.set_ylim(-35,15); ax.legend(loc='lower right',fontsize=8)
ax.set_title('Elkhorn ranch house footprint from 360 panos\nlong axis %.1f deg true; stones dark = seen from 2+ panos'%primary['az'])
fig.savefig('topdown.png',dpi=110,bbox_inches='tight')

# 6. overlays
def proj(p,X):
    d=X[:2]-Pall[p]; r=np.hypot(*d); bt=math.degrees(math.atan2(d[0],d[1]))-thall[p]
    e=math.degrees(math.atan2(X[2]-hall[p],r))+tlall[p][0]*math.cos(bt*D)+tlall[p][1]*math.sin(bt*D)
    return bt,e
def draw(p,segs_list,out,stones=True):
    im=Image.open(f'../panos/{p}.jpg'); Wd,Ht=im.size; im=im.resize((Wd//2,Ht//2)); Wd,Ht=im.size
    dr=ImageDraw.Draw(im); hd=crop.HD[p]
    def pix(bt,e): return ((((bt-hd)/360+0.5)%1)*Wd,(0.5-e/180)*Ht)
    for segs,col,w in segs_list:
        for a,b in segs:
            pts=[pix(*proj(p,a+(b-a)*t)) for t in np.linspace(0,1,120)]
            for q0,q1 in zip(pts[:-1],pts[1:]):
                if abs(q0[0]-q1[0])<Wd/2: dr.line([q0,q1],fill=col,width=w)
    if stones:
        for k,v in S.items():
            u,vv=pix(*proj(p,np.array([v[0],v[1],0.]))); dr.ellipse([u-4,vv-4,u+4,vv+4],outline=(0,255,255)); dr.text((u+5,vv-12),k,fill=(0,255,255))
    im.save(out,quality=85)
def house(corners,wall=2.13,ridge=3.2):
    C=[np.array([c[0],c[1],0.]) for c in corners]; T=[c+np.array([0,0,wall]) for c in C]
    base=[(C[i],C[(i+1)%4]) for i in range(4)]; tops=[(T[i],T[(i+1)%4]) for i in range(4)]; posts=[(C[i],T[i]) for i in range(4)]
    # ridge along long axis (SW-NW is long edge): ridge midpoints of short ends
    rs=(T[0]+T[3])/2+np.array([0,0,ridge-wall]); rn=(T[1]+T[2])/2+np.array([0,0,ridge-wall])
    roof=[(rs,rn),(T[0],rs),(T[3],rs),(T[1],rn),(T[2],rn)]
    return base,tops+posts+roof
b1,w1=house(primary['corners']); b2,_=house(sols['centred']['corners'])
for p in range(1,8):
    draw(p,[(w1,(255,255,255),1),(b1,(255,40,40),2),(b2,(255,170,0),1)],f'overlay_p{p}.jpg')
print(json.dumps({k:res[k] for k in ['row_fit','rectangle_primary','free_width_fit_m','nps_cabin_site_stop_local','gps_offset_m']},indent=1))
print('scale',sc,'h',h)
