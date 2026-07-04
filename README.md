# 剑星 FBX 骨骼修复插件（Blender 5.1.2）

这是为 Blender 5.1.2 移植并汉化的 FBX 插件修改版，新增了用于修复《剑星》（Stellar Blade）倒置骨骼的导出选项。

## 安装

将本仓库 `io_scene_fbx` 文件夹中的内容，替换到 Blender 安装目录中的：

`Blender\5.1\scripts\addons_core\io_scene_fbx`

本分支基于 Blender 上游 `v5.1.2` 的 FBX 插件移植了剑星骨骼修复逻辑。

## 使用说明

如果导入时启用了 Sockets，FBX 导出器将无法正常工作。如果你使用 `.PSK` 格式导入网格，需要在 FModel 中修改这个选项。

![1](https://github.com/user-attachments/assets/7062aee0-5ef3-4213-9cc0-5958c50c2597)

如果你使用 `.uemodel` 格式导入网格，则不需要在 FModel 中额外设置；但导入到 Blender 时必须关闭 `Import Sockets`，可以在 UEFormat Importer 选项卡中禁用它。

![2](https://github.com/user-attachments/assets/ae89f655-44c4-4ce8-bca9-38bc4a6d3458)

导出时，启用 `倒置骨骼修复`，并且务必在 `骨架` 选项卡中禁用 `添加末端骨骼`。

![3](https://github.com/user-attachments/assets/7570ea16-d655-4530-8ce7-33394360191e)

## 致谢

Salt（提供倒置骨骼列表）

Njaecha（代码优化与 GitHub 文件管理）

Heuwu（协助编辑 README 说明）
