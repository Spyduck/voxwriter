
bl_info = {
	"name": "VoxWriter",
	"author": "Spyduck",
	"version": (0,2),
	"blender": (2,80,0),
	"location": "File > Export > MagicaVoxel (.vox)",
	"description": "Export to MagicaVoxel .vox",
	"category": "Export"}

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, FloatProperty
from bpy.types import Operator


class ExportSomeData(Operator, ExportHelper):
	"""Export the selected object to a MagicaVoxel .vox"""
	bl_idname = "export_vox.some_data"
	bl_label = "MagicaVoxel (.vox)"
	bl_options = {'PRESET'}

	# ExportHelper mixin class uses this
	filename_ext = ".vox"

	filter_glob: StringProperty(
		default="*.vox",
		options={'HIDDEN'},
		maxlen=255,  # Max internal buffer length, longer would be clamped.
	)

	# List of operator properties, the attributes will be assigned
	# to the class instance from the operator settings before calling.
	voxel_detail: IntProperty(
		name="Voxel Detail",
		description="Voxel Detail",
		default=32,
		min=1,
		max=256,
	)
	use_default_palette: BoolProperty(
		name="Use default palette",
		description="Use default palette",
		default=False,
	)
	use_selected_objects: BoolProperty(
		name="Selected Objects",
		description="Export selected meshes only",
		default=False,
	)
	use_scene_units: BoolProperty(
		name="Use Scene Units",
		description="Uses the object dimensions as the basis for the chunk size (This only supports a scene up to 256 units!)",
		default=False,
	)
	voxel_unit_scale: FloatProperty(
		name="Scale",
		description="The scale of a voxel in the scene",
		default=1.0,
		min=0.01,
		max=256.0,
	)

	def draw(self, context):
		layout = self.layout

		row = layout.row()
		row.prop(self, "use_selected_objects")

		box = layout.box()
		row = box.row()
		row.label(text="Voxelizer")
		row = box.row()
		row.active = not self.use_scene_units
		row.prop(self, "voxel_detail")
		row = box.row()
		row.prop(self, "use_scene_units")
		row = box.row()
		row.active = self.use_scene_units
		row.prop(self, "voxel_unit_scale")

		box = layout.box()
		row = box.row()
		row.label(text="MagicaVoxel")
		row = box.row()
		row.prop(self, "use_default_palette")

	def execute(self, context):
		from .writer import voxelize
		print("running voxelize...")
		voxelize(context.active_object,
			     self.filepath,
				 vox_detail=max(0,min(256,self.voxel_detail)),
				 use_default_palette=self.use_default_palette,
				 use_selected_objects=self.use_selected_objects,
				 use_scene_units=self.use_scene_units,
				 voxel_unit_scale=self.voxel_unit_scale)
		return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
	self.layout.operator(ExportSomeData.bl_idname, text="MagicaVoxel (.vox)")


def register():
	bpy.utils.register_class(ExportSomeData)
	bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
	bpy.utils.unregister_class(ExportSomeData)
	bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
	register()

	# test call
	bpy.ops.export_vox.some_data('INVOKE_DEFAULT')
