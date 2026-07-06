# SPDX-FileCopyrightText: 2011-2023 Blender Foundation
#
# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "FBX 格式",
    # This is now displayed as the maintainer, so show the foundation.
    # "author": "Campbell Barton, Bastien Montagne, Jens Restemeier, @Mysteryem", # Original Authors
    "author": "Blender Foundation",
    "version": (5, 15, 0),
    "blender": (5, 0, 0),
    "location": "文件 > 导入-导出",
    "description": "FBX 网格、UV、顶点颜色、材质、纹理、相机、灯光和动作的导入导出",
    "warning": "",
    "doc_url": "{BLENDER_MANUAL_URL}/addons/import_export/scene_fbx.html",
    "support": 'OFFICIAL',
    "category": "导入-导出",
}


if "bpy" in locals():
    import importlib
    if "import_fbx" in locals():
        importlib.reload(import_fbx)
    if "export_fbx_bin" in locals():
        importlib.reload(export_fbx_bin)
    if "export_fbx" in locals():
        importlib.reload(export_fbx)


import bpy
import os
from bpy.props import (
    StringProperty,
    BoolProperty,
    FloatProperty,
    EnumProperty,
    CollectionProperty,
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
    orientation_helper,
    path_reference_mode,
    axis_conversion,
    poll_file_object_drop,
)


def get_stellar_blade_json_list(self, context):
    items = []
    json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sb-json")

    if not os.path.isdir(json_dir):
        return [("NONE", "未找到 .json 文件夹", "", 0)]

    try:
        for index, filename in enumerate(sorted(os.listdir(json_dir))):
            if filename.lower().endswith(".json"):
                name = os.path.splitext(filename)[0]
                items.append((name, name, filename, index))

        if not items:
            items = [("NONE", "未找到 .json 文件", "", 0)]
    except OSError as ex:
        items = [("ERROR", f"读取文件夹出错：{ex}", "", 0)]

    return items


class OT_OpenStellarBladeFolder(bpy.types.Operator):
    bl_idname = "wm.open_stellarblade_folder"
    bl_label = "在资源管理器中显示"
    bl_description = "打开包含剑星骨骼 .json 文件的文件夹"

    def execute(self, context):
        json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sb-json")

        if not os.path.isdir(json_dir):
            self.report({'ERROR'}, "未找到 'sb-json' 文件夹。")
            return {'CANCELLED'}

        os.startfile(json_dir)
        return {'FINISHED'}


@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportFBX(bpy.types.Operator, ImportHelper):
    """加载 FBX 文件"""
    bl_idname = "import_scene.fbx"
    bl_label = "导入 FBX"
    bl_options = {'UNDO', 'PRESET'}

    directory: StringProperty(
        subtype='DIR_PATH',
        options={'HIDDEN', 'SKIP_PRESET'},
    )

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    files: CollectionProperty(
        name="文件路径",
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_PRESET'},
    )

    ui_tab: EnumProperty(
        items=(('MAIN', "主要", "主要基础设置"),
               ('ARMATURE', "骨架", "骨架相关设置"),
               ),
        name="界面分类",
        description="导入选项分类",
    )

    use_manual_orientation: BoolProperty(
        name="手动方向",
        description="手动指定方向和缩放，而不是使用 FBX 文件中嵌入的数据",
        default=False,
    )
    global_scale: FloatProperty(
        name="缩放",
        min=0.001, max=1000.0,
        default=1.0,
    )
    bake_space_transform: BoolProperty(
        name="应用变换",
        description="将空间变换烘焙进对象数据，避免目标空间与 Blender 空间不一致时产生不需要的旋转"
        "（警告：实验选项，风险自负，已知会破坏骨架/动画）",
        default=False,
    )

    use_custom_normals: BoolProperty(
        name="自定义法线",
        description="如果可用则导入自定义法线，否则由 Blender 重新计算",
        default=True,
    )
    colors_type: EnumProperty(
        name="顶点颜色",
        items=(('NONE', "无", "不导入颜色属性"),
               ('SRGB', "sRGB", "按 sRGB 色彩空间读取文件颜色"),
               ('LINEAR', "线性", "按线性色彩空间读取文件颜色"),
               ),
        description="导入顶点颜色属性",
        default='SRGB',
    )

    use_image_search: BoolProperty(
        name="搜索图像",
        description="在子目录中搜索关联图像（警告：可能较慢）",
        default=True,
    )

    use_alpha_decals: BoolProperty(
        name="Alpha 贴花",
        description="将带 Alpha 的材质视为贴花（不投射阴影）",
        default=False,
    )
    decal_offset: FloatProperty(
        name="贴花偏移",
        description="偏移 Alpha 网格的几何体",
        min=0.0, max=1.0,
        default=0.0,
    )

    use_anim: BoolProperty(
        name="导入动画",
        description="导入 FBX 动画",
        default=True,
    )
    anim_offset: FloatProperty(
        name="动画偏移",
        description="导入时应用到动画的偏移量，单位为帧",
        default=1.0,
    )

    use_subsurf: BoolProperty(
        name="细分数据",
        description="将 FBX 细分信息作为细分曲面修改器导入",
        default=False,
    )

    use_custom_props: BoolProperty(
        name="自定义属性",
        description="将用户属性作为自定义属性导入",
        default=True,
    )
    use_custom_props_enum_as_string: BoolProperty(
        name="枚举按字符串导入",
        description="将枚举值存储为字符串",
        default=True,
    )

    ignore_leaf_bones: BoolProperty(
        name="忽略末端骨骼",
        description="忽略每条骨骼链末端的最后一根骨骼（用于标记上一根骨骼长度）",
        default=False,
    )
    force_connect_children: BoolProperty(
        name="强制连接子骨骼",
        description="即使计算出的头尾位置不匹配，也强制将子骨骼连接到父骨骼"
        "（对纯关节类型骨架可能有用）",
        default=False,
    )
    automatic_bone_orientation: BoolProperty(
        name="自动骨骼方向",
        description="尝试将主要骨骼轴与子骨骼对齐",
        default=False,
    )
    primary_bone_axis: EnumProperty(
        name="主骨骼轴",
        items=(('X', "X 轴", ""),
               ('Y', "Y 轴", ""),
               ('Z', "Z 轴", ""),
               ('-X', "-X 轴", ""),
               ('-Y', "-Y 轴", ""),
               ('-Z', "-Z 轴", ""),
               ),
        default='Y',
    )
    secondary_bone_axis: EnumProperty(
        name="次骨骼轴",
        items=(('X', "X 轴", ""),
               ('Y', "Y 轴", ""),
               ('Z', "Z 轴", ""),
               ('-X', "-X 轴", ""),
               ('-Y', "-Y 轴", ""),
               ('-Z', "-Z 轴", ""),
               ),
        default='X',
    )

    use_prepost_rot: BoolProperty(
        name="使用前/后旋转",
        description="使用 FBX 变换中的前/后旋转（某些情况下可能需要禁用）",
        default=True,
    )
    mtl_name_collision_mode: EnumProperty(
        name="材质名称冲突",
        items=(("MAKE_UNIQUE", "设为唯一", "将每个 FBX 材质作为唯一的 Blender 材质导入"),
               ("REFERENCE_EXISTING", "引用已有材质",
               "如果已存在同名材质，则引用已有材质而不是重新导入"),
               ),
        default='MAKE_UNIQUE',
        description="导入材质名称与已有材质冲突时的处理方式",
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        import_panel_include(layout, self)
        import_panel_transform(layout, self)
        import_panel_materials(layout, self)
        import_panel_animation(layout, self)
        import_panel_armature(layout, self)

    def execute(self, context):
        keywords = self.as_keywords(ignore=("filter_glob", "directory", "ui_tab", "filepath", "files"))

        from . import import_fbx
        import os

        if self.files:
            ret = {'CANCELLED'}
            for file in self.files:
                path = os.path.join(self.directory, file.name)
                if import_fbx.load(self, context, filepath=path, **keywords) == {'FINISHED'}:
                    ret = {'FINISHED'}
            return ret
        else:
            return import_fbx.load(self, context, filepath=self.filepath, **keywords)

    def invoke(self, context, event):
        return self.invoke_popup(context)


def import_panel_include(layout, operator):
    header, body = layout.panel("FBX_import_include", default_closed=False)
    header.label(text="包含")
    if body:
        body.prop(operator, "use_custom_normals")
        body.prop(operator, "use_subsurf")
        body.prop(operator, "use_custom_props")
        sub = body.row()
        sub.enabled = operator.use_custom_props
        sub.prop(operator, "use_custom_props_enum_as_string")
        body.prop(operator, "use_image_search")
        body.prop(operator, "colors_type")


def import_panel_transform(layout, operator):
    header, body = layout.panel("FBX_import_transform", default_closed=False)
    header.label(text="变换")
    if body:
        body.prop(operator, "global_scale")
        body.prop(operator, "decal_offset")
        row = body.row()
        row.prop(operator, "bake_space_transform")
        row.label(text="", icon='ERROR')
        body.prop(operator, "use_prepost_rot")

        import_panel_transform_orientation(body, operator)


def import_panel_transform_orientation(layout, operator):
    header, body = layout.panel("FBX_import_transform_manual_orientation", default_closed=False)
    header.use_property_split = False
    header.prop(operator, "use_manual_orientation", text="")
    header.label(text="手动方向")
    if body:
        body.enabled = operator.use_manual_orientation
        body.prop(operator, "axis_forward")
        body.prop(operator, "axis_up")


def import_panel_materials(layout, operator):
    header, body = layout.panel("FBX_import_material", default_closed=True)
    header.label(text="材质")
    if body:
        body.prop(operator, "mtl_name_collision_mode")


def import_panel_animation(layout, operator):
    header, body = layout.panel("FBX_import_animation", default_closed=True)
    header.use_property_split = False
    header.prop(operator, "use_anim", text="")
    header.label(text="动画")
    if body:
        body.enabled = operator.use_anim
        body.prop(operator, "anim_offset")


def import_panel_armature(layout, operator):
    header, body = layout.panel("FBX_import_armature", default_closed=True)
    header.label(text="骨架")
    if body:
        body.prop(operator, "ignore_leaf_bones")
        body.prop(operator, "force_connect_children"),
        body.prop(operator, "automatic_bone_orientation"),
        sub = body.column()
        sub.enabled = not operator.automatic_bone_orientation
        sub.prop(operator, "primary_bone_axis")
        sub.prop(operator, "secondary_bone_axis")


@orientation_helper(axis_forward='-Z', axis_up='Y')
class ExportFBX(bpy.types.Operator, ExportHelper):
    """写出 FBX 文件"""
    bl_idname = "export_scene.fbx"
    bl_label = "导出 FBX"
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    use_selection: BoolProperty(
        name="选中对象",
        description="仅导出已选中且可见的对象",
        default=False,
    )
    use_visible: BoolProperty(
        name='可见对象',
        description='仅导出可见对象',
        default=False
    )
    use_active_collection: BoolProperty(
        name="活动集合",
        description="仅导出活动集合及其子集合中的对象",
        default=False,
    )
    collection: StringProperty(
        name="源集合",
        description="仅导出此集合及其子集合中的对象",
        default="",
    )
    global_scale: FloatProperty(
        name="缩放",
        description="缩放所有数据（某些导入器不支持缩放后的骨架！）",
        min=0.001, max=1000.0,
        soft_min=0.01, soft_max=1000.0,
        default=1.0,
    )
    apply_unit_scale: BoolProperty(
        name="应用单位",
        description=(
            "考虑当前 Blender 单位设置"
            "（若未设置，则直接使用原始 Blender 单位值）"
        ),
        default=True,
    )
    apply_scale_options: EnumProperty(
        items=(('FBX_SCALE_NONE', "全部局部",
                "将自定义缩放和单位缩放应用到每个对象变换，FBX 缩放保持 1.0"),
               ('FBX_SCALE_UNITS', "FBX 单位缩放",
                "将自定义缩放应用到每个对象变换，将单位缩放应用到 FBX 缩放"),
               ('FBX_SCALE_CUSTOM', "FBX 自定义缩放",
                "将自定义缩放应用到 FBX 缩放，将单位缩放应用到每个对象变换"),
               ('FBX_SCALE_ALL', "FBX 全部缩放",
                "将自定义缩放和单位缩放应用到 FBX 缩放"),
               ),
        name="应用缩放方式",
        description="指定在生成的 FBX 文件中如何应用自定义缩放和单位缩放"
        "（Blender 会在导入时使用 FBX 缩放检测单位，"
        "但许多其他应用处理方式不同）",
    )

    use_space_transform: BoolProperty(
        name="使用空间变换",
        description="将全局空间变换应用到对象旋转。禁用时仅写入轴空间，所有对象变换保持原样",
        default=True,
    )
    bake_space_transform: BoolProperty(
        name="应用变换",
        description="将空间变换烘焙进对象数据，避免目标空间与 Blender 空间不一致时产生不需要的旋转"
        "（警告：实验选项，风险自负，已知会破坏骨架/动画）",
        default=False,
    )

    object_types: EnumProperty(
        name="对象类型",
        options={'ENUM_FLAG'},
        items=(('EMPTY', "空物体", ""),
               ('CAMERA', "相机", ""),
               ('LIGHT', "灯光", ""),
               ('ARMATURE', "骨架", "警告：不支持复制/组实例"),
               ('MESH', "网格", ""),
               ('OTHER', "其他", "其他几何类型，如曲线、融球等（会转换为网格）"),
               ),
        description="要导出的对象类型",
        default={'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'MESH', 'OTHER'},
    )

    use_mesh_modifiers: BoolProperty(
        name="应用修改器",
        description="将修改器应用到网格对象（骨架修改器除外）- 警告：会阻止形态键导出",
        default=True,
    )
    use_mesh_modifiers_render: BoolProperty(
        name="使用修改器渲染设置",
        description="应用网格对象修改器时使用渲染设置（Blender 2.8 中已禁用）",
        default=True,
    )
    mesh_smooth_type: EnumProperty(
        name="平滑",
        items=(('OFF', "仅法线", "仅导出法线，不写入边或面的平滑数据"),
               ('FACE', "面", "写入面平滑"),
               ('EDGE', "边", "写入边平滑"),
               ('SMOOTH_GROUP', "平滑组", "写入面平滑组"),
               ),
        description="导出平滑信息"
        "（如果目标导入器支持自定义法线，优先使用“仅法线”）",
        default='OFF',
    )
    colors_type: EnumProperty(
        name="顶点颜色",
        items=(('NONE', "无", "不导出颜色属性"),
               ('SRGB', "sRGB", "按 sRGB 色彩空间导出颜色"),
               ('LINEAR', "线性", "按线性色彩空间导出颜色"),
               ),
        description="导出顶点颜色属性",
        default='SRGB',
    )
    prioritize_active_color: BoolProperty(
        name="优先活动颜色",
        description="确保活动颜色最先导出。某些软件可能会丢弃第一个以外的颜色属性",
        default=False,
    )
    use_subsurf: BoolProperty(
        name="导出细分曲面",
        description="将最后一个 Catmull-Rom 细分修改器作为 FBX 细分导出"
        "（即使启用“应用修改器”，也不会应用该修改器）",
        default=False,
    )
    use_mesh_edges: BoolProperty(
        name="松散边",
        description="导出松散边（作为双顶点多边形）",
        default=False,
    )
    use_tspace: BoolProperty(
        name="切线空间",
        description="添加副法线和切线向量，与法线共同组成切线空间"
        "（仅对完全由三角形/四边形组成的网格可靠！）",
        default=False,
    )
    use_triangles: BoolProperty(
        name="三角化面",
        description="将所有面转换为三角形",
        default=False,
    )
    use_custom_props: BoolProperty(
        name="自定义属性",
        description="导出自定义属性",
        default=False,
    )
    add_leaf_bones: BoolProperty(
        name="添加叶骨",
        description="在每条骨骼链末端附加一根最终骨骼，用于指定最后一根骨骼长度"
        "（当你打算从导出的数据编辑骨架时使用）",
        default=False,
    )
    primary_bone_axis: EnumProperty(
        name="主骨骼轴",
        items=(('X', "X 轴", ""),
               ('Y', "Y 轴", ""),
               ('Z', "Z 轴", ""),
               ('-X', "-X 轴", ""),
               ('-Y', "-Y 轴", ""),
               ('-Z', "-Z 轴", ""),
               ),
        default='Y',
    )
    secondary_bone_axis: EnumProperty(
        name="次骨骼轴",
        items=(('X', "X 轴", ""),
               ('Y', "Y 轴", ""),
               ('Z', "Z 轴", ""),
               ('-X', "-X 轴", ""),
               ('-Y', "-Y 轴", ""),
               ('-Z', "-Z 轴", ""),
               ),
        default='X',
    )
    use_armature_deform_only: BoolProperty(
        name="仅变形骨骼",
        description="仅写入变形骨骼（以及拥有变形子骨骼的非变形骨骼）",
        default=True,
    )
    armature_nodetype: EnumProperty(
        name="骨架 FBX 节点类型",
        items=(('NULL', "Null 空节点", "'Null' FBX 节点，类似 Blender 的空物体（默认）"),
               ('ROOT', "Root 根节点", "'Root' FBX 节点，通常表示骨骼链根节点"),
               ('LIMBNODE', "LimbNode 肢体节点", "'LimbNode' FBX 节点，表示两根骨骼之间的常规关节"),
               ),
        description="用于表示 Blender 骨架的 FBX 节点（对象）类型"
        "（除非目标软件有问题，否则建议使用 Null 类型，"
        "其他选项可能无法完美导回 Blender）",
        default='NULL',
    )
    bake_anim: BoolProperty(
        name="烘焙动画",
        description="导出烘焙关键帧动画",
        default=True,
    )
    bake_anim_use_all_bones: BoolProperty(
        name="所有骨骼设关键帧",
        description="强制为所有骨骼至少导出一个动画关键帧"
        "（某些目标应用需要，例如 UE4）",
        default=True,
    )
    bake_anim_use_nla_strips: BoolProperty(
        name="NLA 片段",
        description="如存在未静音的 NLA 片段，则分别导出为独立的 FBX AnimStack，"
        "而不是全局场景动画",
        default=True,
    )
    bake_anim_use_all_actions: BoolProperty(
        name="所有动作",
        description="将每个动作导出为独立的 FBX AnimStack，而不是全局场景动画"
        "（注意：有动画的对象会获得所有兼容动作，其他对象不会获得动画）",
        default=True,
    )
    bake_anim_force_startend_keying: BoolProperty(
        name="强制首尾关键帧",
        description="始终在动画通道的动作开始和结束处添加关键帧",
        default=True,
    )
    bake_anim_step: FloatProperty(
        name="采样率",
        description="动画值的评估频率，单位为帧",
        min=0.01, max=100.0,
        soft_min=0.1, soft_max=10.0,
        default=1.0,
    )
    bake_anim_simplify_factor: FloatProperty(
        name="简化",
        description="烘焙值的简化程度（0.0 表示禁用，数值越高简化越多）",
        min=0.0, max=100.0,  # No simplification to up to 10% of current magnitude tolerance.
        soft_min=0.0, soft_max=10.0,
        default=1.0,  # default: min slope: 0.005, max frame step: 10.
    )
    path_mode: path_reference_mode
    embed_textures: BoolProperty(
        name="嵌入纹理",
        description="将纹理嵌入 FBX 二进制文件（仅适用于“复制”路径模式！）",
        default=False,
    )
    batch_mode: EnumProperty(
        name="批量模式",
        items=(('OFF', "关闭", "将活动场景导出到文件"),
               ('SCENE', "场景", "每个场景导出为一个文件"),
               ('COLLECTION', "集合",
                "每个数据块集合导出为一个文件，不包含子集合内容"),
               ('SCENE_COLLECTION', "场景集合",
                "每个场景中的每个集合导出为一个文件，并包含子集合内容"),
               ('ACTIVE_SCENE_COLLECTION', "活动场景集合",
                "活动场景中的每个集合导出为一个文件，并包含子集合内容"),
               ),
    )
    use_batch_own_dir: BoolProperty(
        name="批量独立目录",
        description="为每个导出的文件创建一个目录",
        default=True,
    )
    use_metadata: BoolProperty(
        name="使用元数据",
        default=True,
        options={'HIDDEN'},
    )
    stellar_blade_fix: BoolProperty(
        name="倒置骨骼修复",
        description="导出剑星所需的骨骼反转修复",
        default=False,
    )
    stellar_blade_skeleton: EnumProperty(
        name="骨骼文件",
        description="从 sb-json 文件夹选择 .json 骨骼文件",
        items=get_stellar_blade_json_list,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        # Are we inside the File browser
        is_file_browser = context.space_data.type == 'FILE_BROWSER'

        export_main(layout, self, is_file_browser)
        export_panel_stellar_blade(layout, self)
        export_panel_include(layout, self, is_file_browser)
        export_panel_transform(layout, self)
        export_panel_geometry(layout, self)
        export_panel_armature(layout, self)
        export_panel_animation(layout, self)

    @property
    def check_extension(self):
        return self.batch_mode == 'OFF'

    def execute(self, context):
        from mathutils import Matrix
        if not self.filepath:
            raise Exception("filepath not set")

        global_matrix = (axis_conversion(to_forward=self.axis_forward,
                                         to_up=self.axis_up,
                                         ).to_4x4()
                         if self.use_space_transform else Matrix())

        keywords = self.as_keywords(ignore=("check_existing",
                                            "filter_glob",
                                            "ui_tab",
                                            ))

        keywords["global_matrix"] = global_matrix

        from . import export_fbx_bin
        return export_fbx_bin.save(self, context, **keywords)


def export_main(layout, operator, is_file_browser):
    row = layout.row(align=True)
    row.prop(operator, "path_mode")
    sub = row.row(align=True)
    sub.enabled = (operator.path_mode == 'COPY')
    sub.prop(operator, "embed_textures", text="", icon='PACKAGE' if operator.embed_textures else 'UGLYPACKAGE')
    if is_file_browser:
        row = layout.row(align=True)
        row.prop(operator, "batch_mode")
        sub = row.row(align=True)
        sub.prop(operator, "use_batch_own_dir", text="", icon='NEWFOLDER')


def export_panel_include(layout, operator, is_file_browser):
    header, body = layout.panel("FBX_export_include", default_closed=False)
    header.label(text="包含")
    if body:
        sublayout = body.column(heading="限制为")
        sublayout.enabled = (operator.batch_mode == 'OFF')
        if is_file_browser:
            sublayout.prop(operator, "use_selection")
            sublayout.prop(operator, "use_visible")
            sublayout.prop(operator, "use_active_collection")

        body.column().prop(operator, "object_types")
        body.prop(operator, "use_custom_props")


def export_panel_transform(layout, operator):
    header, body = layout.panel("FBX_export_transform", default_closed=False)
    header.label(text="变换")
    if body:
        body.prop(operator, "global_scale")
        body.prop(operator, "apply_scale_options")

        body.prop(operator, "axis_forward")
        body.prop(operator, "axis_up")

        body.prop(operator, "apply_unit_scale")
        body.prop(operator, "use_space_transform")
        row = body.row()
        row.prop(operator, "bake_space_transform")
        row.label(text="", icon='ERROR')


def export_panel_geometry(layout, operator):
    header, body = layout.panel("FBX_export_geometry", default_closed=True)
    header.label(text="几何")
    if body:
        body.prop(operator, "mesh_smooth_type")
        body.prop(operator, "use_subsurf")
        body.prop(operator, "use_mesh_modifiers")
        # sub = body.row()
        # sub.enabled = operator.use_mesh_modifiers and False  # disabled in 2.8...
        # sub.prop(operator, "use_mesh_modifiers_render")
        body.prop(operator, "use_mesh_edges")
        body.prop(operator, "use_triangles")
        sub = body.row()
        # ~ sub.enabled = operator.mesh_smooth_type in {'OFF'}
        sub.prop(operator, "use_tspace")
        body.prop(operator, "colors_type")
        body.prop(operator, "prioritize_active_color")


def export_panel_armature(layout, operator):
    header, body = layout.panel("FBX_export_armature", default_closed=True)
    header.label(text="骨架")
    if body:
        body.prop(operator, "primary_bone_axis")
        body.prop(operator, "secondary_bone_axis")
        body.prop(operator, "armature_nodetype")
        body.prop(operator, "use_armature_deform_only")
        body.prop(operator, "add_leaf_bones")


def export_panel_stellar_blade(layout, operator):
    header, body = layout.panel("FBX_export_stellarblade", default_closed=False)
    header.label(text="剑星")

    if body:
        json_items = get_stellar_blade_json_list(operator, bpy.context)
        has_valid_json = json_items and json_items[0][0] not in {"NONE", "ERROR"}

        if not has_valid_json:
            row = body.row()
            row.enabled = False
            row.prop(operator, "stellar_blade_fix")
            row = body.row()
            row.alert = True
            row.label(text="未找到 .json 骨骼文件。", icon='ERROR')
            row = body.row()
            row.enabled = False
            row.prop(operator, "stellar_blade_skeleton")
        else:
            body.prop(operator, "stellar_blade_fix")

            row = body.row(align=True)
            row.prop(operator, "stellar_blade_skeleton", text=".json 文件")
            row.operator("wm.open_stellarblade_folder", text="", icon="FILE_FOLDER")

            if operator.stellar_blade_skeleton == 'CH_P_EVE_01_Skeleton':
                body.label(text="伊芙骨骼 (CH_P_EVE_01_Skeleton)", icon='OUTLINER_OB_ARMATURE')
            elif operator.stellar_blade_skeleton == 'CH_NPC_01_Skeleton':
                body.label(text="莉莉骨骼 (CH_NPC_01_Skeleton)", icon='OUTLINER_OB_ARMATURE')

        body.separator()
        body.label(text="剑星 FBX 修复（Lemi21 与 Njaecha）")


def export_panel_animation(layout, operator):
    header, body = layout.panel("FBX_export_bake_animation", default_closed=True)
    header.use_property_split = False
    header.prop(operator, "bake_anim", text="")
    header.label(text="动画")
    if body:
        body.enabled = operator.bake_anim
        body.prop(operator, "bake_anim_use_all_bones")
        body.prop(operator, "bake_anim_use_nla_strips")
        body.prop(operator, "bake_anim_use_all_actions")
        body.prop(operator, "bake_anim_force_startend_keying")
        body.prop(operator, "bake_anim_step")
        body.prop(operator, "bake_anim_simplify_factor")


def menu_func_import(self, context):
    self.layout.operator(ImportFBX.bl_idname, text="FBX (.fbx)（旧版）")


def menu_func_export(self, context):
    self.layout.operator(ExportFBX.bl_idname, text="FBX (.fbx)")


classes = (
    ImportFBX,
    ExportFBX,
    OT_OpenStellarBladeFolder,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
