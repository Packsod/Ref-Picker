import bpy
import os
import tempfile
import subprocess
from mathutils import Vector
import shutil
from bpy.types import Operator, PropertyGroup, UIList

bl_info = {
    "name": "Ref Picker",
    "author": "Packsod",
    "version": (0, 9, 2),
    "blender": (4, 1, 0),
    "category": "3D View",
    "location": "3D Viewport > Sidebar > Ref Picker",
    "description": "Organize reference images in Blender."
}

class RefPicker:
    @staticmethod
    def ensure_pillow():
        try:
            from PIL import Image
            return True
        except ImportError:
            return False

    @staticmethod
    def install_pillow():
        import sys
        try:
            python_exe = os.path.join(sys.prefix, 'bin', 'python.exe')
            subprocess.check_call([python_exe, "-m", "ensurepip", "--upgrade"])
            subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
            subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "Pillow", "--no-cache-dir"])
            print("Pillow installed successfully.")
        except Exception as e:
            print(f"Failed to install Pillow: {e}")

    @staticmethod
    def get_blend_file_dir():
        return os.path.dirname(bpy.data.filepath)

    @staticmethod
    def get_images_dir():
        return os.path.join(RefPicker.get_blend_file_dir(), "images")

    @staticmethod
    def get_reffolder_objects():
        return [obj for obj in bpy.data.objects if obj.name.startswith("reffolder_")]

    @staticmethod
    def remove_readonly(func, path, _):
        os.chmod(path, 0o777)
        func(path)

    @staticmethod
    def show_popup(text, title="Info", icon='INFO'):
        def _show_popup(self, context):
            layout = self.layout
            for line in text.splitlines():
                layout.label(text=line)
        bpy.context.window_manager.popup_menu(_show_popup, title=title, icon=icon)

    @staticmethod
    def paste_ref_image():
        if not RefPicker.ensure_pillow():
            RefPicker.install_pillow()

        try:
            from PIL import ImageGrab, Image
            import io
            import base64
            import os
            import time

            # Initialize common parameters
            active_obj = bpy.context.active_object
            x_offset = active_obj.location.x if active_obj else 0
            y_offset = active_obj.location.y if active_obj else 0
            objects_per_row = 6
            object_size = 5
            num_objects = 0

            def create_image_object(img, x_offset, y_offset, num_objects, objects_per_row, object_size):
                ref = bpy.data.objects.new(name=img.name, object_data=None)
                ref.empty_display_type = 'IMAGE'
                ref.data = img
                ref.location = (x_offset, y_offset, 0)
                ref.empty_display_size = object_size
                bpy.context.collection.objects.link(ref)
                ref.select_set(True)
                return ref

            # Cancel selection of all objects
            bpy.ops.object.select_all(action='DESELECT')

            # Try to paste as an image first
            try:
                image = ImageGrab.grabclipboard()
                if isinstance(image, Image.Image):
                    temp_dir = bpy.context.preferences.filepaths.temporary_directory
                    if not temp_dir:
                        temp_dir = tempfile.gettempdir()
                    temp_subdir = os.path.join(temp_dir, "clipboard")
                    if not os.path.exists(temp_subdir):
                        os.makedirs(temp_subdir)
                    temp_filename = f"clipboard_image_{int(time.time())}.png"
                    temp_path = os.path.join(temp_subdir, temp_filename)
                    image.save(temp_path)

                    img = bpy.data.images.load(temp_path)
                    create_image_object(img, x_offset, y_offset, num_objects, objects_per_row, object_size)
                    num_objects += 1
                    x_offset += object_size * 1.1  # Add a small gap between images
                    if num_objects % objects_per_row == 0:
                        x_offset = active_obj.location.x if active_obj else 0
                        y_offset -= object_size * 1.1

                    print("Image pasted from clipboard")
                    return
            except Exception as e:
                print(f"Failed to paste image: {e}")

            # If not an image, try to paste as an image path list
            clipboard_content = bpy.context.window_manager.clipboard
            # Remove leading and trailing double quotes from each line
            clipboard_content = clipboard_content.replace('\"', '')
            if '\n' in clipboard_content:
                image_paths = [path.strip() for path in clipboard_content.splitlines()]
                if all(os.path.isfile(path) for path in image_paths):
                    for path in image_paths:
                        img = bpy.data.images.load(path)
                        create_image_object(img, x_offset, y_offset, num_objects, objects_per_row, object_size)
                        num_objects += 1
                        x_offset += object_size * 1.1  # Add a small gap between images
                        if num_objects % objects_per_row == 0:
                            x_offset = active_obj.location.x if active_obj else 0
                            y_offset -= object_size * 1.1

                    print("Images pasted from clipboard")
                    return
            else:
                print("No valid image or image paths in clipboard")
        except ImportError:
            print("Pillow is not installed.")
        except Exception as e:
            print(f"Failed to paste image: {e}")

    @staticmethod
    def sync_images():
        # Check if the blend file is saved
        if not bpy.data.is_saved:
            RefPicker.show_popup("Please save the blend file first.", title="File Not Saved", icon='ERROR')
            return {'CANCELLED'}

        # Check if there are any reffolder objects
        reffolder_objects = RefPicker.get_reffolder_objects()
        if not reffolder_objects:
            bpy.ops.image.help('INVOKE_DEFAULT')
            return {'FINISHED'}

        # Check if there are any image objects
        image_objects = [obj for obj in bpy.data.objects if obj.type == 'EMPTY' and obj.empty_display_type == 'IMAGE']
        if not image_objects:
            RefPicker.show_popup("You need to import ref images first.", title="File Not Saved", icon='ERROR')
            return {'CANCELLED'}

        # Clean up unused data blocks
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        # Define directories
        images_dir = RefPicker.get_images_dir()

        # Create the images directory if it doesn't exist
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)

        # Create a set of associated folder names
        associated_folders = set(reffolder_obj.name.replace("reffolder_", "") for reffolder_obj in reffolder_objects)

        # List all folders in the images directory
        all_folders = set(os.listdir(images_dir))

        # Find unassociated folders
        unassociated_folders = all_folders - associated_folders

        # Process unassociated folders
        for folder_name in unassociated_folders:
            folder_path = os.path.join(images_dir, folder_name)
            if os.path.isdir(folder_path):
                try:
                    shutil.rmtree(folder_path, onerror=RefPicker.remove_readonly)
                    print(f"Deleted folder and its contents: {folder_path}")
                except Exception as e:
                    print(f"Failed to delete folder and its contents: {folder_path} - {e}")

        # Check for overlapping bounding boxes
        if RefPicker.check_overlapping_bboxes(reffolder_objects):
            return {'CANCELLED'}

        # Create subdirectories for each folder object
        reffolder_map = {obj: os.path.join(images_dir, obj.name.replace("reffolder_", "")) for obj in reffolder_objects}
        for folder_path in reffolder_map.values():
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

        images_to_remove = set()
        for image in bpy.data.images:
            if image.source == 'FILE':
                source_file = bpy.path.abspath(image.filepath)
                if not os.path.exists(source_file):
                    print(f"Source file does not exist: {source_file}")
                    continue

                file_name = os.path.basename(source_file)
                file_ext = os.path.splitext(file_name)[1]

                found = False
                for reffolder_obj, reffolder_path in reffolder_map.items():
                    reffolder_bbox_min = reffolder_obj.matrix_world @ Vector(reffolder_obj.bound_box[0])
                    reffolder_bbox_max = reffolder_obj.matrix_world @ Vector(reffolder_obj.bound_box[7])
                    reffolder_x_min, reffolder_y_min = reffolder_bbox_min.x, reffolder_bbox_min.y
                    reffolder_x_max, reffolder_y_max = reffolder_bbox_max.x, reffolder_bbox_max.y

                    for obj in bpy.context.collection.objects:
                        if obj.type == 'EMPTY' and obj.empty_display_type == 'IMAGE' and obj.data == image:
                            obj_location_world = obj.matrix_world.translation
                            x, y, _ = obj_location_world

                            if reffolder_x_min <= x <= reffolder_x_max and reffolder_y_min <= y <= reffolder_y_max:
                                found = True
                                destination_file = os.path.join(reffolder_path, file_name)

                                if os.path.exists(destination_file):
                                    try:
                                        with open(source_file, 'rb') as src, open(destination_file, 'rb') as dst:
                                            if src.read() == dst.read():
                                                print(f"Destination file {destination_file} is the same as source file {source_file}, skipping.")
                                                continue
                                    except Exception as e:
                                        print(f"Failed to compare files {source_file} and {destination_file}: {e}")

                                if not RefPicker.ensure_pillow():
                                    RefPicker.install_pillow()
                                    return
                                try:
                                    from PIL import Image
                                    img = Image.open(source_file)
                                    img.save(destination_file, 'PNG')
                                    print(f"Copied and converted {source_file} to {destination_file}")

                                    new_image = bpy.data.images.load(destination_file)
                                    obj.data = new_image
                                    new_image.filepath = bpy.path.relpath(destination_file)
                                    print(f"Set relative path for {new_image.filepath}")

                                    base_name = os.path.splitext(os.path.basename(new_image.filepath))[0]
                                    if base_name[-1].isdigit():
                                        base_name = base_name.rsplit('.', 1)[0]
                                    new_image.name = base_name
                                    print(f"Renamed image to {new_image.name}")

                                except Exception as e:
                                    print(f"Failed to convert {source_file}: {e}")

                                break

                if not found:
                    images_to_remove.add(image)

        # Remove images that are not associated with any folder
        for image in images_to_remove:
            for obj in bpy.context.collection.objects:
                if obj.type == 'EMPTY' and obj.empty_display_type == 'IMAGE' and obj.data == image:
                    try:
                        bpy.data.objects.remove(obj, do_unlink=True)
                    except ReferenceError as e:
                        print(f"ReferenceError: {e}")
            try:
                bpy.data.images.remove(image, do_unlink=True)
                print(f"Removed image {image.name} due to no associated folder")
            except ReferenceError as e:
                print(f"ReferenceError: {e}")

        # Process each reffolder_obj individually
        for reffolder_obj in reffolder_objects:
            reffolder_name = reffolder_obj.name.replace("reffolder_", "")
            reffolder_path = os.path.join(images_dir, reffolder_name)

            # Check and remove images that are no longer associated with any empty object
            for file_name in os.listdir(reffolder_path):
                if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tga')):
                    file_path = os.path.join(reffolder_path, file_name)
                    referenced = False
                    for obj in bpy.context.collection.objects:
                        if obj.type == 'EMPTY' and obj.empty_display_type == 'IMAGE':
                            obj_location_world = obj.matrix_world.translation
                            if bpy.path.abspath(obj.data.filepath) == file_path:
                                referenced = True
                                break

                    if not referenced:
                        try:
                            os.remove(file_path)
                            print(f"Deleted unused image file: {file_path}")
                        except Exception as e:
                            print(f"Failed to delete unused image file: {file_path} - {e}")

            # Arrange image-containing empty objects in grid order within each folder object
            arranged_objects = []
            for obj in bpy.context.collection.objects:
                if obj.type == 'EMPTY' and obj.empty_display_type == 'IMAGE':
                    obj_location_world = obj.matrix_world.translation
                    obj_bbox_min = obj.matrix_world @ Vector(obj.bound_box[0])
                    obj_bbox_max = obj.matrix_world @ Vector(obj.bound_box[7])
                    x, y, _ = obj_location_world

                    # Check if the object's location is within the folder's bounding box
                    reffolder_bbox_min = reffolder_obj.matrix_world @ Vector(reffolder_obj.bound_box[0])
                    reffolder_bbox_max = reffolder_obj.matrix_world @ Vector(reffolder_obj.bound_box[7])
                    reffolder_x_min, reffolder_y_min = reffolder_bbox_min.x, reffolder_bbox_min.y
                    reffolder_x_max, reffolder_y_max = reffolder_bbox_max.x, reffolder_bbox_max.y

                    if reffolder_x_min <= x <= reffolder_x_max and reffolder_y_min <= y <= reffolder_y_max:
                        arranged_objects.append((obj, obj_location_world))

            # Sort objects by their names (assuming they are prefixed with their image names)
            arranged_objects.sort(key=lambda item: item[0].name)

            # Initialize grid arrangement parameters
            first_row_first_obj_x = reffolder_x_min + 2.5
            y_offset = reffolder_y_max - 2.5
            current_row_x = first_row_first_obj_x

            # Arrange objects in grid
            for i, (obj, location) in enumerate(arranged_objects):
                obj_size = obj.empty_display_size * obj.scale.x

                # Check if there is enough space to place the object in the current row
                if current_row_x + obj_size - 2.5 > reffolder_x_max:
                    current_row_x = first_row_first_obj_x
                    y_offset -= obj_size

                obj.location = (current_row_x, y_offset, 0)
                current_row_x += obj_size + 0.5

        return {'FINISHED'}

    @staticmethod
    def rename_folders(reffolder_objects, new_names):
        for obj, new_name in zip(reffolder_objects, new_names):
            reffolder_name = obj.name.replace("reffolder_", "")
            if reffolder_name != new_name:
                # Check if the new folder name already exists
                blend_file_dir = RefPicker.get_blend_file_dir()
                images_dir = RefPicker.get_images_dir()
                new_reffolder_path = os.path.join(images_dir, new_name)
                if os.path.exists(new_reffolder_path):
                    return f"Folder '{new_reffolder_path}' already exists. Please choose a different name."

                # Rename the object
                obj.name = f"reffolder_{new_name}"
                # Rename the associated folder
                old_reffolder_path = os.path.join(images_dir, reffolder_name)
                if os.path.exists(old_reffolder_path):
                    os.rename(old_reffolder_path, new_reffolder_path)
                    print(f"Renamed folder {old_reffolder_path} to {new_reffolder_path}")
                else:
                    print(f"Folder {old_reffolder_path} does not exist")

                # Update image paths in data
                for image in bpy.data.images:
                    source_file = bpy.path.abspath(image.filepath)
                    if old_reffolder_path in source_file:
                        new_source_file = source_file.replace(old_reffolder_path, new_reffolder_path)
                        image.filepath = bpy.path.relpath(new_source_file)
                        print(f"Updated image path from {source_file} to {new_source_file}")

                # Update text objects
                for child in obj.children:
                    if child.type == 'FONT':
                        child.name = f"3dtext_{new_name}"
                        child.data.body = new_name
                        print(f"Updated text object '{child.name}' to '{new_name}'")                  

        return "Folders renamed successfully"

    @staticmethod
    def check_overlapping_bboxes(reffolder_objects):
        """Check if any of the folder objects have overlapping bounding boxes"""
        overlapping_pairs = []
        for i, obj1 in enumerate(reffolder_objects):
            for obj2 in reffolder_objects[i+1:]:
                # Get the bounding box corners in world coordinates
                bbox1_corners = [obj1.matrix_world @ Vector(corner) for corner in obj1.bound_box]
                bbox2_corners = [obj2.matrix_world @ Vector(corner) for corner in obj2.bound_box]

                # Find the minimum and maximum x, y, z values for both bounding boxes
                bbox1_min = Vector((min(c.x for c in bbox1_corners), min(c.y for c in bbox1_corners), min(c.z for c in bbox1_corners)))
                bbox1_max = Vector((max(c.x for c in bbox1_corners), max(c.y for c in bbox1_corners), max(c.z for c in bbox1_corners)))
                bbox2_min = Vector((min(c.x for c in bbox2_corners), min(c.y for c in bbox2_corners), min(c.z for c in bbox2_corners)))
                bbox2_max = Vector((max(c.x for c in bbox2_corners), max(c.y for c in bbox2_corners), max(c.z for c in bbox2_corners)))

                # Check for overlapping in X, Y, and Z dimensions
                if (bbox1_min.x < bbox2_max.x and bbox1_max.x > bbox2_min.x and
                    bbox1_min.y < bbox2_max.y and bbox1_max.y > bbox2_min.y and
                    bbox1_min.z < bbox2_max.z and bbox1_max.z > bbox2_min.z):
                    overlapping_pairs.append((obj1.name, obj2.name))

        if overlapping_pairs:
            overlapping_info = "\n".join([f"{obj1} and {obj2}" for obj1, obj2 in overlapping_pairs])
            RefPicker.show_popup(f"These image frames overlap each other:\n{overlapping_info}\nplease keep them apart.", title="Overlap Detection", icon='ERROR')
            return True

        return False

class RefPickerRenameFoldersOperator(Operator, PropertyGroup):
    bl_idname = "image.rename_folders"
    bl_label = "Rename Folders"
    bl_description = "Rename associated folders and their corresponding objects"

    reffolder_objects: bpy.props.CollectionProperty(type=PropertyGroup)
    reffolder_names: bpy.props.CollectionProperty(type=PropertyGroup)

    def invoke(self, context, event):
        self.reffolder_objects.clear()
        self.reffolder_names.clear()
        reffolder_objects = RefPicker.get_reffolder_objects()
        if not reffolder_objects:
            bpy.ops.image.help('INVOKE_DEFAULT')
            return {'CANCELLED'}
        for obj in reffolder_objects:
            reffolder_name = obj.name.replace("reffolder_", "")
            item = self.reffolder_objects.add()
            item.name = obj.name
            item_obj = self.reffolder_names.add()
            item_obj.name = reffolder_name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        images_dir = RefPicker.get_images_dir()
        existing_names = set(os.path.basename(f.path) for f in os.scandir(images_dir) if f.is_dir())
        illegal_chars = set(r'<>:"/\|?*')
        for i, item in enumerate(self.reffolder_names):
            row = layout.row(align=True)
            new_name = item.name
            original_name = self.reffolder_objects[i].name.replace("reffolder_", "")
            conflict = False
            illegal_char_found = any(char in new_name for char in illegal_chars)
            duplicate = False
            first_occurrence = next((j for j, name in enumerate(self.reffolder_names) if name.name == new_name), -1)
            if new_name != original_name and new_name in existing_names:
                conflict = True
                row.alert = True  # Highlight the row in red
            if illegal_char_found:
                row.alert = True  # Highlight the row in red
            if first_occurrence != i and new_name != original_name:
                duplicate = True
                row.alert = True  # Highlight the row in red
            if conflict:
                row.label(text="Conflict", icon='ERROR')
            elif illegal_char_found:
                row.label(text="Invalid Characters", icon='ERROR')
            elif duplicate:
                row.label(text="Duplicate", icon='ERROR')
            row.prop(item, "name", text=str(i + 1))

    def execute(self, context):
        bpy.ops.ed.undo_push(message="Rename Folders")
        reffolder_objects = RefPicker.get_reffolder_objects()
        new_names = [item.name for item in self.reffolder_names]
        illegal_chars = set(r'<>:"/\|?*')
        if any(char in name for name in new_names for char in illegal_chars):
            RefPicker.show_popup("Invalid characters found in folder names", title="Invalid Characters", icon='ERROR')
            return {'CANCELLED'}
        conflict_message = RefPicker.rename_folders(reffolder_objects, new_names)
        if conflict_message:
            RefPicker.show_popup(conflict_message, title="File Exists", icon='ERROR')
            return {'CANCELLED'}
        bpy.ops.ed.undo()
        return {'FINISHED'}

    def check(self, context):
        images_dir = RefPicker.get_images_dir()
        existing_names = set(os.path.basename(f.path) for f in os.scandir(images_dir) if f.is_dir())
        illegal_chars = set(r'<>:"/\|?*')
        new_names = [item.name for item in self.reffolder_names]
        for i, new_name in enumerate(new_names):
            original_name = self.reffolder_objects[i].name.replace("reffolder_", "")
            if new_name != original_name and new_name in existing_names:
                return False
            illegal_char_found = any(char in new_name for char in illegal_chars)
            if illegal_char_found:
                return False
            first_occurrence = next((j for j, name in enumerate(new_names) if name == new_name), -1)
            if first_occurrence != i and new_name != original_name:
                return False
        return True

class RefPickerOperator(bpy.types.Operator):
    bl_idname = "image.ref_picker"
    bl_label = "Sync"

    def execute(self, context):
        result = RefPicker.sync_images()
        if result is not None:
            return result
        return {'FINISHED'}


class PasteImageFromClipboardOperator(bpy.types.Operator):
    bl_idname = "image.paste_from_clipboard"
    bl_label = "Paste from Clipboard"

    def execute(self, context):
        RefPicker.paste_ref_image()
        return {'FINISHED'}

class ShowPathInfoOperator(bpy.types.Operator):
    bl_idname = "image.show_path_info"
    bl_label = "Path Info"
    bl_description = "Show paths of associated folders in the clipboard"

    def execute(self, context):
        images_dir = RefPicker.get_images_dir()

        reffolder_objects = RefPicker.get_reffolder_objects()
        paths = []

        for reffolder_obj in reffolder_objects:
            reffolder_name = reffolder_obj.name.replace("reffolder_", "")
            reffolder_path = os.path.join(images_dir, reffolder_name)
            if os.path.exists(reffolder_path):
                paths.append(reffolder_path)

        if paths:
            paths.insert(0, "***Paths***")  # Add placeholder at the beginning
            RefPicker.show_popup("\n".join(paths), title="Path Info has been copied to your clipboard!", icon='INFO')
            bpy.context.window_manager.clipboard = "\n".join(paths)
        else:
            RefPicker.show_popup("No Path Info, because no associated folders was created yet.", title="Path Info doesn't exist", icon='INFO')

        return {'FINISHED'}

class RefPickerPanel(bpy.types.Panel):
    bl_label = "Ref Picker"
    bl_idname = "IMAGE_PT_ref_picker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Ref Picker'

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("image.ref_picker", text="Sync")
        row.label(text="", icon='BLANK1')  # placeholder

        row = layout.row(align=True)
        row.operator("image.rename_folders", text="Rename")
        row.operator("image.show_path_info", text="", icon='INFO')
        row = layout.row()
        row.prop(context.window_manager, "enable_ctrl_v_paste", text="Enable Ctrl+V Paste")

class ModalHandlerOperator(bpy.types.Operator):
    bl_idname = "image.modal_handler"
    bl_label = "Modal Handler"

    def modal(self, context, event):
        if event.type == 'V' and event.value == 'PRESS' and event.ctrl and context.window_manager.enable_ctrl_v_paste:
            RefPicker.paste_ref_image()
            return {'RUNNING_MODAL'}  # Restart the modal handler
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

# New operator for the "help" button
class HelpOperator(bpy.types.Operator):
    bl_idname = "image.help"
    bl_label = "Help"
    bl_description = "simple guide book"

    def execute(self, context):
        # Check if there are any objects with prefix 'reffolder_'
        if any(obj.name.startswith('reffolder_') for obj in bpy.data.objects):
            return {'CANCELLED'}

        # New mesh data
        verts = [(-20.0, -20.0, 0.0), (20.0, -20.0, 0.0), (-20.0, 20.0, 0.0), (20.0, 20.0, 0.0)]
        faces = [[0, 1, 3, 2]]

        # Create mesh data
        mesh = bpy.data.meshes.new("refoldermesh")
        mesh.from_pydata(verts, [], faces)

        # Object information
        objects_info = [
            ("reffolder_01-frame-name-must", (-23, 25, 0)),
            ("reffolder_02-be-prefixed", (23, 25, 0)),
            ("reffolder_03-with-reffolder", (-23, -25, 0)),
            ("reffolder_04-and-underscore", (23, -25, 0))
        ]

        # Function to create a 3D text object
        def create_text_object(parent, text, size=5, location=(0, 0, 0)):
            text_curve = bpy.data.curves.new(name="text_curve", type='FONT')
            text_curve.body = text
            text_curve.size = size
            text_curve.align_x = 'CENTER'
            text_curve.align_y = 'BOTTOM'
            text_obj = bpy.data.objects.new(name="text_object", object_data=text_curve)
            text_obj.location = location
            bpy.context.collection.objects.link(text_obj)
            if parent:
                text_obj.parent = parent

        for name, loc in objects_info:
            ob = bpy.data.objects.new(name, mesh)
            ob.location = loc
            bpy.context.collection.objects.link(ob)
            create_text_object(ob, name[10:], location=(0, -25, 0))
            ob.modifiers.new(name="Wireframe", type='WIREFRAME').thickness = 0.5

        # Create "put images into the frames" 3D text object
        create_text_object(
            None,
            "enable the Ctrl + V checkbox, paste images into Blender.\nput images into the frames,\nthen press Sync, images will be backed up.",
            size=5,
            location=(0, 48, 0)
        )

        print("Objects have been created, positioned, and modified with wireframe modifiers.")
        return {'FINISHED'}

def modal_handler_delayed_call(dummy):
    bpy.app.handlers.depsgraph_update_post.remove(modal_handler_delayed_call)
    if bpy.context.window_manager.enable_ctrl_v_paste:
        bpy.ops.image.modal_handler('INVOKE_DEFAULT')

def enable_ctrl_v_paste_update(self, context):
    if self.enable_ctrl_v_paste:  # self is WindowManager now
        bpy.ops.image.modal_handler('INVOKE_DEFAULT')

# Register and unregister functions
def register():
    bpy.utils.register_class(RefPickerOperator)
    bpy.utils.register_class(PasteImageFromClipboardOperator)
    bpy.utils.register_class(ShowPathInfoOperator)
    bpy.utils.register_class(RefPickerPanel)
    bpy.utils.register_class(ModalHandlerOperator)
    bpy.utils.register_class(RefPickerRenameFoldersOperator)
    bpy.utils.register_class(HelpOperator)
    bpy.types.WindowManager.enable_ctrl_v_paste = bpy.props.BoolProperty(
        name="Enable Ctrl+V Paste",
        default=False,
        update=enable_ctrl_v_paste_update,
        options={'SKIP_SAVE'}
    )

    # Only call modal_handler when running in Blender
    if not bpy.app.background:
        bpy.app.handlers.depsgraph_update_post.append(modal_handler_delayed_call)

def unregister():
    bpy.utils.unregister_class(RefPickerOperator)
    bpy.utils.unregister_class(PasteImageFromClipboardOperator)
    bpy.utils.unregister_class(ShowPathInfoOperator)
    bpy.utils.unregister_class(RefPickerPanel)
    bpy.utils.unregister_class(ModalHandlerOperator)
    bpy.utils.unregister_class(RefPickerRenameFoldersOperator)
    bpy.utils.unregister_class(HelpOperator)
    del bpy.types.WindowManager.enable_ctrl_v_paste

    # Only call modal_handler when running in Blender
    if not bpy.app.background:
        bpy.app.handlers.depsgraph_update_post.remove(modal_handler_delayed_call)

if __name__ == "__main__":
    register()
