import json, math, sys, numpy as np, rasterio
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, map_coordinates, zoom
from pyproj import Transformer
import matplotlib; matplotlib.use('Agg'); import matplotlib.cm as cm

S = '/tmp/claude-0/-home-claude/4cec2ed1-e3f9-5b51-a27d-73f13cf5ade5/scratchpad'
SHIFT_N = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0   # optional house shift along N (m) for testing
OUT = sys.argv[2] if len(sys.argv) > 2 else S + '/combined/site_evidence.jpg'
t = Transformer.from_crs(4326, 26913, always_xy=True)
d = rasterio.open(S + '/lidar/dem_ground_tin_0p5m.tif'); z = d.read(1).astype(float); B = d.bounds
z = np.where(np.isfinite(z), z, np.nanmean(z))
lrm = z - gaussian_filter(z, 10)
gy, gx = np.gradient(z * 3, 0.5)
def hs(az, alt=35):
    s = np.arctan(np.hypot(gx, gy)); a = np.arctan2(-gx, gy); A = math.radians(az); L = math.radians(alt)
    return np.clip(math.sin(L) * np.cos(s) + math.cos(L) * np.sin(s) * np.cos(A - a), 0, 1)
H = (hs(315) + hs(45) + hs(135) + hs(225)) / 4
L = np.clip((lrm + 0.3) / 0.6, 0, 1)
base = (cm.RdBu_r(L)[:, :, :3] * 0.55 + H[:, :, None] * 0.45)
U = 3
base = np.stack([zoom(base[:, :, i], U, order=1) for i in range(3)], -1)
h, w = base.shape[:2]; res = 0.5 / U
def topx(x, y): return ((x - B.left) / res, (B.top - y) / res)

m = json.load(open(S + '/layout/elkhorn_map_features.json'))['features_px']   # (x=col, y=row); +x ~ north, +y ~ east
hc = np.mean([m['house_outline_' + k] for k in ('SW', 'NW', 'NE', 'SE')], axis=0)
R = json.load(open(S + '/footprint/results.json'))
ctr = R['rectangle_alternative_centred']['center']; cx, cy = t.transform(ctr['lon'], ctr['lat'])
reg_rot = json.load(open(S + '/layout/registered_features.json'))['rotation_deg']
rot = math.radians(reg_rot); k = 0.3048 / 5
axis = math.radians(11.7)
cx += SHIFT_N * math.sin(axis); cy += SHIFT_N * math.cos(axis)

def map2utm(px, py):
    dn = (px - hc[0]) * k; de = (py - hc[1]) * k
    return cx + de * math.cos(rot) + dn * math.sin(rot), cy - de * math.sin(rot) + dn * math.cos(rot)

X = B.left + (np.arange(w) + 0.5) * res; Y = B.top - (np.arange(h) + 0.5) * res
XX, YY = np.meshgrid(X, Y); E = XX - cx; N = YY - cy
de = E * math.cos(rot) - N * math.sin(rot); dn = E * math.sin(rot) + N * math.cos(rot)
mp = np.asarray(Image.open(S + '/layout/img/taylor/beaubien_taylor_map_mosaic_approx.png').convert('L')).astype(float) / 255
v = map_coordinates(mp, [de / k + hc[1], dn / k + hc[0]], order=1, cval=1.0)   # [row=y, col=x]
ink = np.clip((0.7 - v) / 0.4, 0, 1)
over = base * (1 - ink[:, :, None])
img = Image.fromarray((over * 255).astype(np.uint8)); dr = ImageDraw.Draw(img)
F = lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', s)

cs = R['rectangle_alternative_centred']['corners']
pts = [topx(*t.transform(cs[q]['lon'], cs[q]['lat'])) for q in ('SW', 'NW', 'NE', 'SE')]
dr.polygon(pts, outline=(255, 215, 0), width=4)
for s in R['stones'].values():
    x, y = topx(*t.transform(s['lon'], s['lat'])); dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(255, 230, 0), outline=(0, 0, 0))
cl = json.load(open(S + '/lidar/candidates.json'))['candidates']
for q in cl:
    if q['label'] in ('D1', 'D2', 'D13', 'M12', 'M15', 'D5'):
        x, y = topx(q['E'], q['N']); r = max(14, math.sqrt(q['area_m2']) / res / 2)
        col = (0, 210, 255) if q['type'].startswith('d') else (255, 60, 200)
        dr.ellipse([x - r, y - r, x + r, y + r], outline=col, width=5)
        dr.text((x + r + 4, y - 12), q['label'], fill=col, font=F(24), stroke_width=3, stroke_fill=(0, 0, 0))
names = {'well_center': 'well', 'barn': 'barn', 'blacksmith': 'blacksmith shop', 'dugout': 'dugout', 'round_corral_center_snubbing_post': 'round corral'}
feat = dict(m)
feat['barn'] = [(a + b) / 2 for a, b in zip(*m['barn_hatched_bbox_approx'])]
feat['blacksmith'] = [(a + b) / 2 for a, b in zip(m['blacksmith_SW'], m['blacksmith_NE'])]
feat['dugout'] = [(a + b) / 2 for a, b in zip(*m['dugout_bbox'])]
for kf, lab in names.items():
    x, y = topx(*map2utm(*feat[kf]))
    dr.line([(x - 12, y), (x + 12, y)], fill=(255, 255, 255), width=4); dr.line([(x, y - 12), (x, y + 12)], fill=(255, 255, 255), width=4)
    dr.text((x + 10, y + 8), lab, fill=(255, 255, 255), font=F(22), stroke_width=3, stroke_fill=(0, 0, 0))
cxp, cyp = topx(cx, cy)
box = (int(cxp - 115 / res), int(cyp - 80 / res), int(cxp + 60 / res), int(cyp + 115 / res))
im = img.crop(box); d2 = ImageDraw.Draw(im); W, Hh = im.size
d2.rectangle([20, Hh - 50, 20 + 20 / res, Hh - 38], fill=(255, 255, 255))
d2.text((20, Hh - 80), '20 m', fill=(255, 255, 255), font=F(24), stroke_width=3, stroke_fill=(0, 0, 0))
d2.polygon([(W - 40, 20), (W - 55, 60), (W - 25, 60)], fill=(255, 255, 255))
d2.text((W - 50, 64), 'N', fill=(255, 255, 255), font=F(24), stroke_width=2, stroke_fill=(0, 0, 0))
leg = ['Yellow: house footprint from the 360s; dots = stones',
       'Black lines + white crosses: 1957/59 excavation plan',
       'Blue rings: lidar pits   Pink rings: lidar mounds',
       'Background: 2021 USGS lidar, red higher / blue lower']
d2.rectangle([10, 10, 10 + 700, 10 + 4 * 30 + 14], fill=(0, 0, 0))
for i, l in enumerate(leg): d2.text((20, 18 + i * 30), l, fill=(255, 255, 255), font=F(20))
im.save(OUT, quality=86); print(im.size)
