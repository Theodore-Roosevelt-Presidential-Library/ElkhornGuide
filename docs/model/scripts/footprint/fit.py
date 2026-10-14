import numpy as np, json
from scipy.optimize import least_squares
import solve
WEST=['F','G','H','A']; EAST=['J','L','K']
def fit_lines(S):
    # two parallel lines: n.p = c_w (west), c_e (east); n=(cos a, -sin a) where a=long-axis azimuth
    def r(x):
        a,cw,ce=x; n=np.array([np.cos(a),-np.sin(a)])
        return [n@np.array(S[s])-cw for s in WEST]+[n@np.array(S[s])-ce for s in EAST]
    sol=least_squares(r,[0.2,-0.5,9.5]); a,cw,ce=sol.x
    u=np.array([np.sin(a),np.cos(a)]); n=np.array([np.cos(a),-np.sin(a)])
    along={s:float(u@np.array(S[s])) for s in S}; across={s:float(n@np.array(S[s])-cw) for s in S}
    return dict(az=np.degrees(a)%360,width=ce-cw,cw=cw,ce=ce,rms=float(np.sqrt(np.mean(np.square(sol.fun)))),along=along,across=across,u=u,n=n)
def run(HP=1.5,shift=0.0,TLS=1.0):
    solve.SHADOW={1:shift,2:shift,5:shift}
    x=least_squares(lambda x: solve.res(x,HP=HP,TLS=TLS),solve.init(),loss='soft_l1',f_scale=2.0).x
    return x,solve.unpack(x)
if __name__=='__main__':
    x,(P,th,h,tl,S)=run()
    f=fit_lines(S)
    print('nominal az %.1f width %.2f rms %.2f'%(f['az'],f['width'],f['rms']))
    for s in sorted(S): print(s,'along %.2f across %.2f'%(f['along'][s],f['across'][s]))
    rows=[]
    for HP in [1.35,1.5,1.65]:
        for sh in [-3,0,3]:
            for T in [0.3,1.0]:
                x,(P,th,h,tl,S)=run(HP,sh,T); g=fit_lines(S)
                ext=[g['along'][s] for s in WEST+EAST]
                rows.append((HP,sh,T,g['az'],g['width'],min(ext),max(ext),g['rms']))
                print('HP %.2f shift %+d tilt %.1f -> az %.1f width %.2f span %.1f..%.1f rms %.2f'%rows[-1])
    R=np.array(rows); print('az range',R[:,3].min(),R[:,3].max(),'width range',R[:,4].min(),R[:,4].max(),'length span',(R[:,6]-R[:,5]).min(),(R[:,6]-R[:,5]).max())
