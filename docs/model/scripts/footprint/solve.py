import numpy as np, json
from scipy.optimize import least_squares
D=np.pi/180
# observations: (pano, stone, bearing_deg (tag frame), elev_deg, sig_b, sig_e)
OBS=[
 # pano 1
 (1,'A',358.6,-23.4,0.8,0.8),   # flat round slab N, broken edge
 (1,'B', 35.2,-34.0,0.8,1.0),   # rounded boulder NE (very close)
 (1,'C', 60.4,-10.9,0.6,0.6),   # dusty flat slab ENE (p1)
 (1,'D', 76.4, -3.6,0.6,0.5),   # far flat slab E (p1 only)
 (1,'I',105.0, -5.1,0.6,0.5),   # buried flat slab ESE
 (1,'J',143.8, -5.3,0.6,0.5),   # flat slab at foot of juniper
 (1,'E',177.2, -2.5,0.5,0.5),   # small stone beside S path
 (1,'F',195.0, -6.05,0.5,0.5),  # small dark angular stone SSW
 (1,'G',199.3,-12.8,0.6,0.6),   # square raised block SSW
 (1,'H',207.4,-26.5,0.8,0.8),   # large layered slab SW (very close)
 # pano 5
 (5,'K',184.5,-21.3,0.6,0.7),   # rounded dark lichen boulder (p5 only)
 (5,'L',187.4,-10.5,0.6,0.6),   # flat slab S (p5 only)
 (5,'J',192.0, -6.7,0.6,0.5),
 (5,'F',226.8, -4.7,0.6,0.5),
 (5,'G',236.7, -5.7,0.5,0.5),
 (5,'H',247.7, -7.0,0.6,0.5),
 (5,'B',270.7,-11.2,0.5,0.5),
 (5,'M',276.6,-20.1,0.7,0.7),   # light flat slab close W of p5 (was tentatively =C; residuals 5 sigma, so kept separate)
 (5,'A',278.8, -8.6,0.6,0.5),
 # pano 2
 (2,'F',351.1, -4.9,0.5,0.4),
 (2,'G',354.4, -3.2,0.4,0.4),
 (2,'H',356.7, -2.4,0.4,0.4),
]
PAN=[1,2,5]
SHADOW={1:0.,2:0.,5:0.}   # common absolute heading prior (sun check ~ +-3 deg)
SKY={(5,1):(0.0,0.7),(2,1):(0.5,1.2)}  # relative heading from butte summit (deg, sigma)
STONES=sorted(set(o[1] for o in OBS))
def unpack(x):
    i=0; P={1:(0.,0.)}
    for p in [2,5]: P[p]=(x[i],x[i+1]); i+=2
    th={};h={};tl={}
    for p in PAN: th[p]=x[i]; h[p]=x[i+1]; tl[p]=(x[i+2],x[i+3]); i+=4
    S={}
    for s in STONES: S[s]=(x[i],x[i+1]); i+=2
    return P,th,h,tl,S
def res(x, HP=1.5, HS=0.15, THS=3.0, TLS=1.0, use_shadow=True):
    P,th,h,tl,S=unpack(x); r=[]
    for p,s,b,e,sb,se in OBS:
        dx=S[s][0]-P[p][0]; dy=S[s][1]-P[p][1]
        bp=np.degrees(np.arctan2(dx,dy))-th[p]
        rr=np.hypot(dx,dy)
        bm=b
        db=(bp-bm+180)%360-180
        # tilt model: elevation offset = a*cos(beta)+c*sin(beta)
        ep=-np.degrees(np.arctan2(h[p],rr)) + tl[p][0]*np.cos(b*D)+tl[p][1]*np.sin(b*D)
        r+= [db/sb, (ep-e)/se]
    for p in PAN:
        m=SHADOW[p] if use_shadow else 0.
        r+=[(th[p]-m)/THS,(h[p]-HP)/HS,tl[p][0]/TLS,tl[p][1]/TLS]
    for (a,b),(v,sg) in SKY.items(): r.append((th[a]-th[b]-v)/sg)
    return np.array(r)
def init():
    x=[1.5,-30, 10.6,2.6]
    for p in PAN: x+=[0,1.5,0,0]
    guess={'A':(0,3.3),'B':(1.2,1.8),'C':(6.5,3.7),'D':(22,5),'I':(15.7,-4.2),'J':(9.2,-12.6),'E':(1.6,-33),'F':(-3.5,-13.2),'G':(-2,-6),'H':(-1.3,-2.6),'K':(10.3,-1),'L':(9.6,-5.1),'M':(5.2,2.6)}
    for s in STONES: x+=list(guess[s])
    return np.array(x,float)
if __name__=='__main__':
    sol=least_squares(res,init(),loss='soft_l1',f_scale=2.0)
    P,th,h,tl,S=unpack(sol.x)
    r=res(sol.x)
    print('cost',sol.cost)
    for k,(o) in enumerate(OBS): print(o[0],o[1],'res_b %.2f sig  res_e %.2f sig'%(r[2*k],r[2*k+1]))
    for p in PAN: print('pano',p,'pos',np.round(P[p],2),'dθ %.2f'%th[p],'h %.2f'%h[p],'tilt',np.round(tl[p],2))
    for s in STONES: print(s,np.round(S[s],2))
    # covariance
    J=sol.jac; cov=np.linalg.pinv(J.T@J)
    sd=np.sqrt(np.diag(cov))
    print('sd pano2',sd[0:2],'pano5',sd[2:4])
    json.dump({'x':sol.x.tolist(),'sd':sd.tolist()},open('solve_out.json','w'))
