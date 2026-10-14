"""Bake the interior lighting of the ranch house into lightmaps for the web viewer.

For every interior surface object: add a second UV set ('LightMap', smart-projected and packed), then let Cycles bake
DIFFUSE direct+indirect light only (irradiance, no surface colour) under the same lights as the stills: afternoon sun
and sky, daylight through each window, the banked fire and the lamps. The viewer multiplies each surface's texture by
its lightmap, so it shows the renders' soft bounce light, shadows and firelight at any camera position.

Lightmaps are stored as sRGB PNGs of irradiance / SCALE (decode: srgb->linear, x SCALE).
Usage: python3 bake.py  ->  out/ar/lightmaps/*.png, out/ar/lightmaps.json, and the scene saved for export."""
import sys, os, json, math, time
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import numpy as np
from PIL import Image, ImageFilter
import lib, scene, interior

OUT = lib.M + '/out/ar/lightmaps'
os.makedirs(OUT, exist_ok=True)
SCALE = 4.0
DENSITY = float(os.environ.get('LM_DENSITY', 42))      # lightmap texels per metre
SAMPLES = int(os.environ.get('LM_SAMPLES', 96))
SKIP = {'interior_glass', 'interior_flame', 'interior_ember', 'interior_interior', 'interior_nickel', 'interior_bone2',
        'interior_book', 'interior_pole'}


def targets():
    out = []
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        g = o.name.split('_')[0]
        if (g in ('interior', 'ceiling') or o.name == 'house_ilog') and o.name not in SKIP:
            out.append(o)
    return out


def lightmap_uv(o):
    me = o.data
    base = me.uv_layers[0]
    lm = me.uv_layers.new(name='LightMap')
    me.uv_layers.active = lm
    base.active_render = True
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def size_for(o):
    area = sum(p.area for p in o.data.polygons)
    px = math.sqrt(area) * DENSITY * 1.25          # packing loss
    return int(min(2048, max(128, 2 ** math.ceil(math.log2(max(px, 1))))))


def bake_one(o):
    res = size_for(o)
    img = bpy.data.images.new('LM_' + o.name, res, res, float_buffer=True)
    nodes = []
    for slot in o.material_slots:
        mt = slot.material
        n = mt.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img
        uvn = mt.node_tree.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'LightMap'
        mt.node_tree.links.new(uvn.outputs['UV'], n.inputs['Vector'])
        mt.node_tree.nodes.active = n
        nodes.append((mt, n, uvn))
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    o.data.uv_layers.active = o.data.uv_layers['LightMap']
    t0 = time.time()
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=6, margin_type='EXTEND', use_clear=True)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(res, res, 4)[::-1, :, :3]
    for mt, n, uvn in nodes:
        mt.node_tree.nodes.remove(n); mt.node_tree.nodes.remove(uvn)
    o.data.uv_layers.active = o.data.uv_layers[0]
    # light denoise: small blur (lightmaps are low-frequency), then encode
    enc = np.clip(px / SCALE, 0, 1) ** (1 / 2.2)
    im = Image.fromarray((enc * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0 if res >= 512 else 0.6))
    fn = f'{o.name}.png'
    im.save(f'{OUT}/{fn}', optimize=True)
    bpy.data.images.remove(img)
    print(f'baked {o.name} {res}px {time.time() - t0:.0f}s mean {float(px.mean()):.3f}', flush=True)
    return fn, res


if __name__ == '__main__':
    mats, objs = scene.build_all(site=True, context=False, inside=True)
    for o in list(bpy.data.objects):
        if o.name.startswith('ground'):
            bpy.data.objects.remove(o)
    scene.world(strength=0.6)
    scene.sun(135, 40, 3.6)
    interior.interior_lights()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 4
    tg = targets()
    print('targets', len(tg), flush=True)
    manifest = {'scale': SCALE, 'exposure_stops': 1.0, 'uv': 'TEXCOORD_1', 'maps': {}}
    only = os.environ.get('LM_ONLY')
    for o in tg:
        lightmap_uv(o)
    for o in tg:
        if only and o.name not in only.split(','):
            continue
        fn, res = bake_one(o)
        manifest['maps'][o.name] = {'file': fn, 'size': res}
        json.dump(manifest, open(lib.M + '/out/ar/lightmaps.json', 'w'), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=lib.M + '/out/elkhorn_baked.blend')
    print('done', flush=True)
