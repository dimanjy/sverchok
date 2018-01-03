# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import os
from os.path import join
import shutil
from glob import glob

import bpy
from bpy.props import StringProperty, BoolProperty

from sverchok.utils.sv_IO_panel_tools import write_json, create_dict_of_tree, import_tree
from sverchok.utils.logging import debug, info, error, exception
from sverchok.utils import sv_gist_tools
from sverchok.utils import sv_IO_panel_tools

def get_presets_directory():
    presets = join(bpy.utils.user_resource('DATAFILES', path='sverchok/presets', create=True))
    if not os.path.exists(presets):
        os.makedirs(presets)
    return presets

def get_preset_path(name):
    presets = get_presets_directory()
    return join(presets, name + ".json")

def get_preset_paths():
    presets = get_presets_directory()
    return list(sorted(glob(join(presets, "*.json"))))

class SvPreset(object):
    def __init__(self, name=None, path=None):
        if name is None and path is None:
            raise Exception("Either name or path must be specified when initializing SvPreset")
        self._name = name
        self._path = path

    def get_name(self):
        if self._name is not None:
            return self._name
        else:
            name = os.path.basename(self._path)
            name,_ = os.path.splitext(name)
            self._name = name
            return name

    def set_name(self, new_name):
        self._name = new_name
        self._path = get_preset_path(new_name)

    name = property(get_name, set_name)

    def get_path(self):
        if self._path is not None:
            return self._path
        else:
            path = get_preset_path(self._name)
            self._path = path
            return path

    def set_path(self, new_path):
        name = os.path.basename(new_path)
        name,_ = os.path.splitext(name)
        self._name = name
        self._path = new_path

    path = property(get_path, set_path)

    def draw_operator(self, layout, id_tree):
        op = layout.operator("node.tree_importer_silent", text=self.name)
        op.id_tree = id_tree
        op.filepath = self.path

def get_presets():
    result = []
    for path in get_preset_paths():
        result.append(SvPreset(path=path))
    return result

class SvSaveSelected(bpy.types.Operator):
    """
    Save selected nodes as a preset
    """

    bl_idname = "node.sv_save_selected"
    bl_label = "Save selected tree part"
    bl_options = {'INTERNAL'}

    preset_name = StringProperty(name = "Name",
            description = "Preset name")

    id_tree = StringProperty()

    def execute(self, context):
        if not self.id_tree:
            msg = "Node tree is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        if not self.preset_name:
            msg = "Preset name is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        ng = bpy.data.node_groups[self.id_tree]

        nodes = list(filter(lambda n: n.select, ng.nodes))
        if not len(nodes):
            msg = "There are no selected nodes to export"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        layout_dict = create_dict_of_tree(ng, selected=True)
        destination_path = get_preset_path(self.preset_name)
        write_json(layout_dict, destination_path)
        msg = 'exported to: ' + destination_path
        self.report({"INFO"}, msg)
        info(msg)

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class SvRenamePreset(bpy.types.Operator):
    """
    Change the name of preset
    """

    bl_idname = "node.sv_preset_rename"
    bl_label = "Rename"
    bl_options = {'INTERNAL'}

    old_name = StringProperty(name = "Old name",
            description = "Preset name")

    new_name = StringProperty(name = "New name",
            description = "New preset name")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_name")

    def execute(self, context):
        if not self.old_name:
            msg = "Old preset name is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        if not self.new_name:
            msg = "New preset name is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        old_path = get_preset_path(self.old_name)
        new_path = get_preset_path(self.new_name)

        if os.path.exists(new_path):
            msg = "Preset named `{}' already exists. Refusing to rewrite existing preset.".format(self.new_name)
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        
        os.rename(old_path, new_path)
        info("Renamed `%s' to `%s'", old_path, new_path)
        self.report({'INFO'}, "Renamed `{}' to `{}'".format(self.old_name, self.new_name))

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        self.new_name = self.old_name
        return wm.invoke_props_dialog(self)

class SvDeletePreset(bpy.types.Operator):
    """
    Delete existing preset
    """

    bl_idname = "node.sv_preset_delete"
    bl_label = "Do you really want to delete this preset? This action cannot be undone."
    bl_options = {'INTERNAL'}

    preset_name = StringProperty(name = "Preset name",
            description = "Preset name")

    def execute(self, context):
        if not self.preset_name:
            msg = "Preset name is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        path = get_preset_path(self.preset_name)

        os.remove(path)
        info("Removed `%s'", path)
        self.report({'INFO'}, "Removed `{}'".format(self.preset_name))

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_confirm(self, event)

class SvPresetToGist(bpy.types.Operator):
    """
    Export preset to Gist
    """

    bl_idname = "node.sv_preset_to_gist"
    bl_label = "Export preset to Gist"
    bl_options = {'INTERNAL'}

    preset_name = StringProperty(name = "Preset name",
            description = "Preset name")

    def execute(self, context):
        if not self.preset_name:
            msg = "Preset name is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        path = get_preset_path(self.preset_name)

        gist_filename = self.preset_name + ".json"
        gist_description = self.preset_name
        with open(path, 'rb') as jsonfile:
            gist_body = jsonfile.read().decode('utf8')

        try:
            gist_url = sv_gist_tools.main_upload_function(gist_filename, gist_description, gist_body, show_browser=False)
            context.window_manager.clipboard = gist_url   # full destination url
            info(gist_url)
            self.report({'WARNING'}, "Copied gist URL to clipboad")
            sv_gist_tools.write_or_append_datafiles(gist_url, gist_filename)
        except Exception as err:
            exception(err)
            self.report({'ERROR'}, "Error uploading the gist, check your internet connection!")
            return {'CANCELLED'}
        finally:
            return {'FINISHED'}

class SvPresetToFile(bpy.types.Operator):
    """
    Export preset to outer file
    """

    bl_idname = "node.sv_preset_to_file"
    bl_label = "Export preset to file"
    bl_options = {'INTERNAL'}

    preset_name = StringProperty(name = "Preset name",
            description = "Preset name")

    filepath = StringProperty(
        name="File Path",
        description="Path where preset should be saved to",
        maxlen=1024, default="", subtype='FILE_PATH')

    filter_glob = StringProperty(
        default="*.json",
        options={'HIDDEN'})

    def execute(self, context):
        if not self.preset_name:
            msg = "Preset name is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        if not self.filepath:
            msg = "Target file path is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        existing_path = get_preset_path(self.preset_name)
        shutil.copy(existing_path, self.filepath)
        msg = "Saved `{}' as `{}'".format(self.preset_name, self.filepath)
        info(msg)
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SvPresetFromFile(bpy.types.Operator):
    """
    Import preset from JSON file
    """

    bl_idname = "node.sv_preset_from_file"
    bl_label = "Import preset from file"
    bl_options = {'INTERNAL'}

    preset_name = StringProperty(name = "Preset name",
            description = "Preset name")

    filepath = StringProperty(
        name="File Path",
        description="Path where preset should be saved to",
        maxlen=1024, default="", subtype='FILE_PATH')

    filter_glob = StringProperty(
        default="*.json",
        options={'HIDDEN'})

    def execute(self, context):
        if not self.preset_name:
            msg = "Preset name is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        if not self.filepath:
            msg = "Source file path is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        target_path = get_preset_path(self.preset_name)
        shutil.copy(self.filepath, target_path)
        msg = "Imported `{}' as `{}'".format(self.filepath, self.preset_name)
        info(msg)
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SvPresetFromGist(bpy.types.Operator):
    """
    Import preset from Gist
    """

    bl_idname = "node.sv_preset_from_gist"
    bl_label = "Import preset from Gist"
    bl_options = {'INTERNAL'}

    gist_id = StringProperty(name = "Gist ID",
            description = "Gist identifier (or full URL)")

    preset_name = StringProperty(name = "Preset name",
            description = "Preset name")

    def execute(self, context):
        if not self.preset_name:
            msg = "Preset name is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        if not self.gist_id:
            msg = "Gist ID is not specified"
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        gist_data = sv_IO_panel_tools.load_json_from_gist(self.gist_id, self)
        target_path = get_preset_path(self.preset_name)
        if os.path.exists(target_path):
            msg = "Preset named `{}' already exists. Refusing to rewrite existing preset.".format(self.preset_name)
            error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        
        with open(target_path, 'wb') as jsonfile:
            gist_data = json.dumps(gist_data, sort_keys=True, indent=2).encode('utf8')
            jsonfile.write(gist_data)

        msg = "Imported `{}' as `{}'".format(self.gist_id, self.preset_name)
        info(msg)
        self.report({'INFO'}, msg)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        self.gist_id = context.window_manager.clipboard
        return wm.invoke_props_dialog(self)

def draw_presets_ops(layout, id_tree=None, presets=None, context=None):
    if presets is None:
        presets = get_presets()

    if id_tree is None:
        if context is None:
            raise Exception("Either id_tree or context must be provided for draw_presets_ops()")
        ntree = context.space_data.node_tree
        id_tree = ntree.name

    for preset in presets:
        preset.draw_operator(layout, id_tree)

class SvUserPresetsPanel(bpy.types.Panel):
    bl_idname = "SvUserPresetsPanel"
    bl_label = "Presets"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'TOOLS'
    bl_category = 'Presets'
    use_pin = True

    @classmethod
    def poll(cls, context):
        try:
            return context.space_data.node_tree.bl_idname == 'SverchCustomTreeType'
        except:
            return False

    def draw(self, context):
        layout = self.layout
        ntree = context.space_data.node_tree
        panel_props = ntree.preset_panel_properties

        if any(node.select for node in ntree.nodes):
            layout.operator('node.sv_save_selected', text="Save Preset", icon='SAVE_PREFS').id_tree = ntree.name
            layout.separator()

        presets = get_presets()
        if len(presets):
            layout.prop(panel_props, 'manage_mode', toggle=True)
            layout.separator()

        if panel_props.manage_mode:
            col = layout.column(align=True)
            col.operator("node.sv_preset_from_gist", icon='URL')
            col.operator("node.sv_preset_from_file", icon='IMPORT')

            layout.label("Manage presets:")
            for preset in presets:
                name = preset.name

                row = layout.row(align=True)
                row.label(text=name)

                gist = row.operator('node.sv_preset_to_gist', text="", icon='URL')
                gist.preset_name = name

                export = row.operator('node.sv_preset_to_file', text="", icon="EXPORT")
                export.preset_name = name

                rename = row.operator('node.sv_preset_rename', text="", icon="GREASEPENCIL")
                rename.old_name = name

                delete = row.operator('node.sv_preset_delete', text="", icon='CANCEL')
                delete.preset_name = name

        else:
            layout.label("Use preset:")
            draw_presets_ops(layout, ntree.name, presets)

class SvUserPresetsPanelProps(bpy.types.PropertyGroup):
    manage_mode = BoolProperty(name = "Manage Presets",
            description = "Presets management mode",
            default = False)

classes = [
        SvSaveSelected,
        SvUserPresetsPanelProps,
        SvPresetFromFile,
        SvPresetFromGist,
        SvRenamePreset,
        SvDeletePreset,
        SvPresetToGist,
        SvPresetToFile,
        SvUserPresetsPanel
    ]

def register():
    for clazz in classes:
        bpy.utils.register_class(clazz)

    bpy.types.NodeTree.preset_panel_properties = bpy.props.PointerProperty(
        name="preset_panel_properties", type=SvUserPresetsPanelProps)

def unregister():
    del bpy.types.NodeTree.preset_panel_properties

    for clazz in reversed(classes):
        bpy.utils.unregister_class(clazz)

