import crop,sys
from PIL import Image
p=int(sys.argv[1]); e0=float(sys.argv[2]); e1=float(sys.argv[3]); sc=float(sys.argv[4]); seg=float(sys.argv[5])
HD=crop.HD[p]; n=int(360/seg); per=int(sys.argv[6])
ims=[]
for k in range(n):
    b0=HD-180+seg*k
    fn=f'crops/tmp_{p}_{k}.jpg'; crop.crop(p,b0,b0+seg,e0,e1,sc,5,fn); ims.append(Image.open(fn))
for g in range(0,n,per):
    grp=ims[g:g+per]; W=max(i.width for i in grp); H=sum(i.height+6 for i in grp)
    out=Image.new('RGB',(W,H),(255,255,255)); y=0
    for i in grp: out.paste(i,(0,y)); y+=i.height+6
    out.save(f'crops/strip_p{p}_{g//per}.jpg',quality=88); print(f'crops/strip_p{p}_{g//per}.jpg',out.size)
