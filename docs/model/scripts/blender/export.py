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
        if 'x_albedo' not in mat:
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


if __name__ == '__main__':
    mats, objs = scene.build_all(site=True)
    for o in list(bpy.data.objects):
        if o.name.startswith('ground'):
            bpy.data.objects.remove(o)
    simplify_materials()
    # origin at the centre of the house footprint (15, 30 ft); ground level z = 0
    off = Vector((-15 * FT, -30 * FT, 0))
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.data.transform(__import__('mathutils').Matrix.Translation(off))
    export(AR + '/elkhorn_house.glb', {'house', 'props'})
    export(AR + '/elkhorn_site.glb', {'house', 'props', 'barn', 'shed', 'blacksmith', 'dugout', 'well', 'corral', 'fences'})
    json.dump({
        'model_origin': 'centre of the 60 x 30 ft house footprint at grade (house coords 15, 30 ft)',
        'origin_lat': 47.2419083, 'origin_lon': -103.6222558,
        'model_plus_y_azimuth_deg_true': 11.7,
        'model_plus_x_azimuth_deg_true': 101.7,
        'units': 'metres; glTF +Y up, model north (+Y in Blender) exported as glTF -Z',
        'absolute_accuracy_m': 12, 'relative_accuracy_m': '0.3-0.5 at the foundation stones',
        'source': 'docs/model/footprint.json rectangle_primary'}, open(AR + '/geo.json', 'w'), indent=1)
