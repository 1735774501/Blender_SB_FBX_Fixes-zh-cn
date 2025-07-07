Modified Blender FBX Addon for Blender 4.4 that has a new setting for fixing the inverted bones from Stellar Blade.

To install, replace the contents of `Blender\4.4\scripts\addons_core\io_scene_fbx` with the contents of the `io_scene_fbx` folder in this repository.

The FBX Exporter won't work if you import with Sockets enabled. In case you're importing meshes with .PSK format, its required for you to change this option inside FModel.
![1](https://github.com/user-attachments/assets/7062aee0-5ef3-4213-9cc0-5958c50c2597)

In case you're using .uemodel for Mesh formats, there's nothing to do in FModel, but you'll need to make sure you have the 'Import Sockets' turned OFF, when importing your mesh to blender, you can disable it in the .Uemodel Importer tab.
![2](https://github.com/user-attachments/assets/ae89f655-44c4-4ce8-bca9-38bc4a6d3458)

when exporting, tick enable the 'Inverted Bones Fix', and ALWAYS disable the 'Add Leaf Bones' in the Armature Tab.

![3](https://github.com/user-attachments/assets/7570ea16-d655-4530-8ce7-33394360191e)







Huge thanks to: 
Salt (Providing a list with the inverted bones)
Njaecha (Code optimization and managing the github files)
Heuwu (Helped on editing instructions in Readme page)
