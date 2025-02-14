# Ref Picker

## a simple image organizer implemented in Blender.

![01.png](/images/ref-picker-img01.png)

## Purpose:

I usually load a lot of images and feed them to the diffusion models in ComfyUI. The batch loader node in ComfyUI can't add or delete images from folders. Using multiple image loader nodes may seem like a viable approach, but it is cumbersome and affects performance.

## Solution:

Inspired by PureRef, but not a reference image tool in the general sense, Ref Picker offers the added advantage of real-time management for multiple image folders. Ref Picker allows users to manage multiple image groups through an overview view and sync changes with corresponding folders, ensuring that the images can be easily utilized later in other pipelines. making it particularly useful for organizing image datasets.

![ref-picker-ani01](/images/ref-picker-ani01.gif)

##### Real-time syncing

![op.png](/images/ref-picker-img02-optimized.png)

Instead of manage images in ComfyUI, handle them in Blender, which eliminates the need for many redundant image loader nodes.
* * *

## **Changelog:**

update 0, 9, 2

- Fixed inconsistency between the checkbox display status and the actual status.
- Improved the template, now add adaptive image frame name 3D text
- Add a placeholder to the 1st line in path info

* * *

## **Installation:**

Download ref_picker.py and install it in Blender by going to Preferences > Add-ons > Install from Disk, then selecting the downloaded file from your disk.

Alternatively, you can run it directly by copying ref_picker.py code into the Blender text editor and executing it, without install it.

* * *

## **Usage:**

- Save the current .blend file first.
- Ensure there's an "Image Frame" (a mesh with a "reffolder_" prefix). If not, the Sync button will add a template.

&nbsp;

## **function introduction for each button**

- ### `Sync`    Organizes images, synchronizing operations with folders.
    
    - Saves images to the corresponding folder when placed in an Image Frame.
    - Deletes images and files when removed from an Image Frame.
    - Moves images between folders.
    - Deletes all related folders when an Image Frame is removed.
    - Converts image paths to relative for easy migration.
- ### `Rename`    Edit name of each Image Frame and folder, handling resulting path changes automatically.
    
    - Use this button instead of direct renaming to prevent breaking object-frame-folder associations.
    - It contains a set of detection rules to prevent potential naming errors, including detection of name conflicts, duplications, and illegal characters.
- ### `Enable Ctrl + V paste `    Paste single or multiple images from clipboard into Blender.
    
    - To make clipboard work, need to check/recheck it manually.
    - Supports alpha channels, but not videos.
    - Supports online and local images, pasting list in batches.
    - Assigns new names for single pasted images based on time.
- ### **`Path INFO`**    Display path information
    
    - Pops up with absolute paths of all managed image folders.
    - Copies paths to clipboard for easy loading.

* * *

**Limitations & Recommendations:**

- Images lose metadata when saved.
- Image name must be within 63 characters o be saved.
- Currently can't copy/paste images to other software.
- Works with Windows 11, Blender 4.1 and later, other OS compatibility unknown.
-  Recommend separate directory for new projects.
- Deleted files are permanently removed; be sure to backup files.

* * *

**Known issues and solutions:**

- If you are unable to delete the folder as expected with the addon, it is likely due to insufficient permissions. Ensure that you have full read/write access.
- The addon will automatically install Pillow into your Blender Python environment to support image pasting. If Pillow installation fails, you may need to clean up your Blender Python environment. The simplest way to do this is to reinstall Blender.
