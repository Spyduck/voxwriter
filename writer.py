import bpy, mathutils.geometry, bmesh, math, time, traceback
from mathutils.bvhtree import BVHTree
from mathutils import Vector
from mathutils.geometry import barycentric_transform

import numpy as np
from .pyvox.models import Vox, Color, get_default_palette
from .pyvox.writer import VoxWriter

image_tuples = {}

def TriangulateMesh( obj ):
	bm = bmesh.new()
	bm.from_mesh( obj.data )
	bmesh.ops.triangulate( bm, faces=bm.faces[:] )
	bm.to_mesh( obj.data )
	bm.free()
	
# With help from https://blender.stackexchange.com/a/79251
def get_color_from_geometry(obj, ray_origin, ray_direction, orig_scene=None, location=None, polygon_index=-1):
	global image_tuples
	
	#raycast, or use polygon_index and location if already available
	if not location or polygon_index == -1:
		if not orig_scene:
			dg = bpy.context.evaluated_depsgraph_get()
			orig_scene = bpy.context.scene.evaluated_get(dg)
		success, location, normal, polygon_index, object, matrix = orig_scene.ray_cast(bpy.context.view_layer, ray_origin, ray_direction, distance=0.002)
		if not success:
			return None
	
	# Find the UV map part corresponding to polygon_index
	slots = obj.material_slots
	material_index = obj.data.polygons[polygon_index].material_index
	# if no material exists
	if material_index >= len(slots) or material_index == -1:
		return [0.8, 0.8, 0.8]
	material = slots[obj.data.polygons[polygon_index].material_index].material
	image = get_material_image(material)
	# if no texture exists
	if not image:
		color = get_material_color(material)
		return [color[0], color[1], color[2]]
	
	# get UV map vertices indices
	verticesIndices = obj.data.polygons[polygon_index].vertices
	p1, p2, p3 = [obj.data.vertices[verticesIndices[i]].co for i in range(3)]
	uvMap = obj.data.uv_layers[obj.data.uv_layers.keys()[0]]
	uv1, uv2, uv3 = [uvMap.data[obj.data.polygons[polygon_index].loop_indices[i]].uv for i in range(3)]
	uv1 = Vector((uv1[0], uv1[1], 0))
	uv2 = Vector((uv2[0], uv2[1], 0))
	uv3 = Vector((uv3[0], uv3[1], 0))
	transformed_point = barycentric_transform( location, p1, p2, p3, uv1, uv2, uv3 )
	
	width = image.size[0]
	height = image.size[1]
	
	uv = Vector((transformed_point.x % 1.0, transformed_point.y % 1.0))
	
	coord = (
		round((uv[0] % 1.0) * width-1),
		round((uv[1] % 1.0) * height-1),
	)
	pindex = int(((width * int(coord[1])) + int(coord[0])) * 4)
	
	# store images as tuples to avoid recreating the object each loop
	if image.name not in image_tuples:
		print('Adding image', image.name)
		image_tuples[image.name] = tuple(image.pixels)
	color = image_tuples[image.name][pindex:pindex+4]
	
	return color

def get_material_image(material):
	try:
		if material:
			socket = material.node_tree.nodes.get('Principled BSDF',None)
			if socket:
				for link1 in socket.inputs['Base Color'].links:
					link_node = link1.from_node
					if 'image' in dir(link_node):
						return link_node.image
					else:
						if link_node.name == 'Mix':
							for input in link_node.inputs:
								if input.is_linked:
									for link2 in input.links:
										if 'image' in dir(link2.from_node):
											return link2.from_node.image
	except:
		print(traceback.format_exc())
		return None
	return None

def try_add_color_to_palette(new_color, palette, color_threshold=24):
	if len(palette) >= 254:
		return palette, nearest_color_index(new_color, palette)
	for color in palette:
		if color_distance(new_color, color) <= color_threshold:
			return palette, nearest_color_index(new_color, palette)
	palette.append(new_color)
	return palette, (len(palette)-1)

def get_material_color(material):
	if material:
		if material.name:
			if material.use_nodes:
				for n in material.node_tree.nodes:
					if n.type == 'BSDF_PRINCIPLED':
						return n.inputs[0].default_value
						for input in n.inputs:
							if input.name == 'Base Color':
								color = input.default_value
								return (color[0], color[1], color[2], color[3])
	return (0.8, 0.8, 0.8, 1.0)

def get_closest_point(p, obj, max_dist=1.84467e+19):
	# max_dist = 1.84467e+19
	result, location, normal, face = obj.closest_point_on_mesh(p, distance=max_dist)
	return result, location, normal, face

def distance(c1, c2):
	(r1,g1,b1) = c1
	(r2,g2,b2) = c2
	return math.sqrt((r1 - r2)**2 + (g1 - g2) ** 2 + (b1 - b2) **2)

def color_distance(c1, c2):
	(r1,g1,b1) = c1.r, c1.g, c1.b
	(r2,g2,b2) = c2.r, c2.g, c2.b
	return math.sqrt((r1 - r2)**2 + (g1 - g2) ** 2 + (b1 - b2) **2)

def find_center(o):
	vcos = [ o.matrix_world @ v.co for v in o.data.vertices ]
	findCenter = lambda l: ( max(l) + min(l) ) / 2

	x,y,z  = [ [ v[i] for v in vcos ] for i in range(3) ]
	center = [ findCenter(axis) for axis in [x,y,z] ]

	return tuple(center)

def find_bounds(o):
	vcos = [ o.matrix_world @ v.co for v in o.data.vertices ]
	findCenter = lambda l: ( max(l) + min(l) ) / 2

	x,y,z  = [ [ v[i] for v in vcos ] for i in range(3) ]
	bbox_min = [ min(axis) for axis in [x,y,z] ]
	bbox_max = [ max(axis) for axis in [x,y,z] ]

	return tuple(bbox_min), tuple(bbox_max)

def nearest_color(color, palette):
	colors_dict = {}
	for i in range(len(palette)):
		colors_dict[i] = palette[i]
	closest_colors = sorted(colors_dict, key=lambda point: color_distance(color, colors_dict[point]))
	return colors_dict[closest_colors[0]]
	
def nearest_color_index(color, palette):
	color = nearest_color(color, palette)
	return palette.index(color)

def voxelize(obj, file_path, vox_detail=32, use_default_palette=False, use_selected_objects=False, use_scene_units=False, voxel_unit_scale=1.0):
	global image_tuples
	image_tuples = {}
	last_time = time.time()

	print('Converting to vox')
	previous_selection = bpy.context.selected_objects

	if not use_selected_objects:
		bpy.ops.object.select_all(action='SELECT')

	source = obj
	source_name = obj.name

	for o in bpy.context.selected_objects:
		if o.type != "MESH":
			o.select_set(False)
	
	bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":"TRANSLATION"})
	bpy.ops.object.join()
	bpy.context.object.name = source_name+'_voxelized'
	bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
	bpy.ops.object.convert(target='MESH')
	
	target_name = bpy.context.object.name
	target = bpy.data.objects[target_name]
	TriangulateMesh(target)
	
	# voxelize

	vox_size = max(target.dimensions) / vox_detail
	bbox_min, bbox_max = find_bounds(target)

	if use_scene_units:
		vox_size = 1.0/voxel_unit_scale
		vox_detail = max(0,min(256,round(max(target.dimensions))))
	
	half_size = vox_size * 0.5

	a = np.zeros((vox_detail, vox_detail, vox_detail), dtype=int)
	
	dg = bpy.context.evaluated_depsgraph_get()
	orig_scene = bpy.context.scene.evaluated_get(dg)
	
	if not use_default_palette:
		palette = []
	else:
		palette = get_default_palette()[1:256]
		print('Default palette length', len(palette))
	
	for x1 in range(0,vox_detail):
		print(str(int(x1 / vox_detail * 100))+'%...')
		x = bbox_min[0] + x1 * vox_size + half_size
		if x > bbox_max[0] + vox_size:
			break
		for y1 in range(0,vox_detail):
			y = bbox_min[1] + y1 * vox_size + half_size
			if y > bbox_max[1] + vox_size:
				break
			for z1 in range(0,vox_detail):
				z = bbox_min[2] + z1 * vox_size + half_size
				if z > bbox_max[2] + vox_size:
					break
				inside, inside_location, inside_normal, inside_face = get_closest_point(Vector((x,y,z)), target, max_dist=half_size*1.42)
				if inside:
					inside = (inside_location[0], inside_location[1], inside_location[2])
					vox_min = (x-half_size,y-half_size,z-half_size)
					vox_max = (x+half_size,y+half_size,z+half_size)
					if inside > vox_min and inside < vox_max:
						location = (inside_location[0] + inside_normal[0] * 0.001,
							inside_location[1] + inside_normal[1] * 0.001,
							inside_location[2] + inside_normal[2] * 0.001)
						normal = (-inside_normal[0], -inside_normal[1], -inside_normal[2])
						color = get_color_from_geometry(target, location, normal, orig_scene=orig_scene, location=inside_location, polygon_index=inside_face)
						if color:
							if len(color) == 4 and color[3] < 0.1:
								continue
							color = Color(int(color[0]*255), int(color[1]*255), int(color[2]*255), 255)
							threshold = max(7, min(12, len(palette) * 0.65))
							palette, color_index = try_add_color_to_palette(color, palette, color_threshold=threshold)
							#color_index = nearest_color_index(color, palette[1:])
							a[y1,(vox_detail-1)-z1,x1] = color_index+1

	vox = Vox.from_dense(a)
	print('Palette length', len(palette))
	vox.palette = palette
	VoxWriter(file_path, vox).write()
	print('100%... Exported to', file_path)
	
	# delete temporary target
	bpy.ops.object.select_all(action='DESELECT')
	target.select_set(True)
	bpy.ops.object.delete()
	bpy.ops.object.select_all(action='DESELECT')
	source.select_set(True)

	for o in previous_selection:
		o.select_set(True)

	bpy.context.view_layer.objects.active = source

	print('Took', int(time.time() - last_time), 'seconds')
