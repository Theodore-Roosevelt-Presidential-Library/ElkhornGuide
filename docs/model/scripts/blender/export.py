"""Export the reconstruction for web AR: GLB (Android / WebXR / model-viewer) with baked-tint 1K/512 textures.
Usage: python3 export.py   -> out/ar/elkhorn_house.glb, elkhorn_site.glb, geo.json"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector
from PIL import Image
import numpy as np
import lib, scene
from lib import FT

AR = lib.M + '/out/ar'; TEX = AR + '/tex'
os.makedirs(TEX, exist_ok=True)
BIG = {'log_walls', 'shingles', 'round_logs', 'porch_floor', 'sod_roof', 'poles', 'posts'}


def bake_image(path, tint, size, kind, name):
    out = f'{TEX}/{name}_{kind}.jpg'
    if os.path.exists(out):
        return out
    im = Image.open(path)
    im = im.convert('L' if kind == 'rough' else 'RGB').resize((size, size), Image.LANCZOS)
    if kind == 'albedo' and tint and tint != [1.0, 1.0, 1.0]:
        a = np.asarray(im).astype(np.float32) / 255.
        lin = a ** 2.2 * np.array(tint, np.float32)          # tint is applied in linear space in the shader
        im = Image.fromarray((np.clip(lin, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8))
    im.save(out, quality=86 if kind != 'normal' else 92)
    return out


def simplify_materials():
    for mat in bpy.data.materials:
        if 'x_flat_rgb' in mat:          # procedural fur -> flat colour for glTF
            nt = mat.node_tree
            for n in list(nt.nodes):
                if n.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'):
                    nt.nodes.remove(n)
            nt.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*mat['x_flat_rgb'], 1)
            continue
        if 'x_albedo' not in mat:
            continue
        if mat.get('x_alpha'):
            nt = mat.node_tree; bsdf = nt.nodes['Principled BSDF']
            for n in list(nt.nodes):
                if n.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'):
                    nt.nodes.remove(n)
            src = Image.open(mat['x_albedo']).convert('RGBA').resize((256, 256), Image.LANCZOS)
            outp = f'{TEX}/{mat.name}_rgba.png'; src.save(outp)
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(outp)
            nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color']); nt.links.new(t.outputs['Alpha'], bsdf.inputs['Alpha'])
            try:
                mat.surface_render_method = 'DITHERED'
            except Exception:
                pass
            continue
        size = 1024 if mat.name in BIG else 512
        nt = mat.node_tree
        for n in list(nt.nodes):
            if n.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'):
                nt.nodes.remove(n)
        bsdf = nt.nodes['Principled BSDF']
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(bake_image(mat['x_albedo'], list(mat['x_tint']), size, 'albedo', mat.name))
        nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
        if mat['x_rough']:
            r = nt.nodes.new('ShaderNodeTexImage'); r.image = bpy.data.images.load(bake_image(mat['x_rough'], None, size // 2, 'rough', mat.name))
            r.image.colorspace_settings.name = 'Non-Color'
            nt.links.new(r.outputs['Color'], bsdf.inputs['Roughness'])
        else:
            bsdf.inputs['Roughness'].default_value = mat['x_rough_value']
        if mat['x_normal']:
            n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(bake_image(mat['x_normal'], None, size, 'normal', mat.name))
            n.image.colorspace_settings.name = 'Non-Color'
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = min(1.0, mat['x_normal_strength'])
            nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])


def export(path, groups):
    for o in bpy.data.objects:
        o.select_set(o.type == 'MESH' and o.name.split('_')[0] in groups)
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
              export_image_format='JPEG', export_draco_mesh_compression_enable=True,
              export_draco_mesh_compression_level=6)
    try:
        bpy.ops.export_scene.gltf(**kw, export_vertex_color='ACTIVE')
    except TypeError:
        bpy.ops.export_scene.gltf(**kw, export_colors=True)
    print('wrote', path, os.path.getsize(path) // 1024, 'KB')


def terrain_glb(path):
    """Low-poly context terrain (2021 lidar) with slope/height-coloured vertices + river surface, for the viewer only."""
    import numpy as np, terrain as T
    d, meta = T.load()
    xs, ys, Z = d['near_xs'], d['near_ys'], d['near_Z']
    Z = T.flatten(xs, ys, Z, {k: 0.0 for k in T.PADS})
    st = 4; xs, ys, Z = xs[::st], ys[::st], Z[::st, ::st]
    nx, ny = len(xs), len(ys)
    gy, gx = np.gradient(Z, ys[1] - ys[0], xs[1] - xs[0]); slope = np.hypot(gx, gy)
    V = [((x - 15) * FT, (y - 30) * FT, Z[j, i] * FT) for j, y in enumerate(ys) for i, x in enumerate(xs)]
    F = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new('terrain'); me.from_pydata(V, [], F)
    col = me.color_attributes.new('Col', 'BYTE_COLOR', 'POINT')
    grass = np.array([0.42, 0.40, 0.26]); clay = np.array([0.55, 0.5, 0.42]); bank = np.array([0.5, 0.45, 0.35])
    for j in range(ny):
        for i in range(nx):
            s_ = min(1.0, max(0.0, (slope[j, i] - 0.35) / 0.5))
            c = grass * (1 - s_) + clay * s_
            if Z[j, i] < meta['water_ft'] + 3: c = bank
            col.data[j * nx + i].color = (*(c ** 2.2), 1)   # store linear values (glTF COLOR_0 is linear)
    mt = bpy.data.materials.new('terrain_vc'); mt.use_nodes = True
    nt = mt.node_tree; va = nt.nodes.new('ShaderNodeVertexColor'); va.layer_name = 'Col'
    nt.links.new(va.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color']); nt.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0
    me.materials.append(mt)
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new('terrain', me); bpy.context.scene.collection.objects.link(ob)
    wl = (meta['water_ft'] + 0.6) * FT; r = 1300 * FT
    wm = bpy.data.meshes.new('river'); wm.from_pydata([(-r, -r, wl), (r, -r, wl), (r, r, wl), (-r, r, wl)], [], [(0, 1, 2, 3)])
    wmat = bpy.data.materials.new('river'); wmat.use_nodes = True
    wmat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.24, 0.24, 0.2, 1)
    wmat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.15
    wm.materials.append(wmat); wo = bpy.data.objects.new('river', wm); bpy.context.scene.collection.objects.link(wo)
    for o in bpy.data.objects:
        o.select_set(o.name in ('terrain', 'river'))
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_vertex_color='ACTIVE')
    print('wrote', path, os.path.getsize(path) // 1024, 'KB')


if __name__ == '__main__':
    mats, objs = scene.build_all(site=True, context=False, inside=True)
    for o in list(bpy.data.objects):
        if o.name.startswith('ground'):
            bpy.data.objects.remove(o)
    simplify_materials()
    off = Vector((-15 * FT, -30 * FT, 0))
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.data.transform(__import__('mathutils').Matrix.Translation(off))
    H = {'house', 'props', 'interior'}
    export(AR + '/elkhorn_house.glb', H | {'roof', 'ceiling'})
    export(AR + '/elkhorn_house_open.glb', H)
    export(AR + '/elkhorn_site.glb', H | {'roof', 'ceiling', 'barn', 'shed', 'blacksmith', 'dugout', 'well', 'corral', 'fences'})
    export(AR + '/elkhorn_site_open.glb', H | {'barn', 'shed', 'blacksmith', 'dugout', 'well', 'corral', 'fences'})
    terrain_glb(AR + '/elkhorn_terrain.glb')
