"""Export GLBs from the baked scene (keeps the LightMap UVs as TEXCOORD_1)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector, Matrix
import lib, export
from lib import FT
bpy.ops.wm.open_mainfile(filepath=lib.M + '/out/elkhorn_baked.blend')
export.simplify_materials()
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.data.transform(Matrix.Translation(Vector((-15 * FT, -30 * FT, 0))))
H = {'house', 'props', 'interior'}
O = {'barn', 'shed', 'blacksmith', 'dugout', 'well', 'corral', 'fences'}
export.export(export.AR + '/elkhorn_house.glb', H | {'roof', 'ceiling'})
export.export(export.AR + '/elkhorn_house_open.glb', H)
export.export(export.AR + '/elkhorn_site.glb', H | {'roof', 'ceiling'} | O)
export.export(export.AR + '/elkhorn_site_open.glb', H | O)
