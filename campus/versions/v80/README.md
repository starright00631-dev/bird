# BNBU 校园可编辑 GIS / 3D · v80（2026-11-12）

本工程**继承 v79 / v78 的已集成主模型**；未重做旧 v10，不从 2025 手绘图生成无测绘依据的坐标。v10 的源代码/GLB/GPKG/QA 另作为历史参考，保留完整来源链。本轮以实际源网格检查优先，修正了六处过去被当作物理道路的推断连路资产的科学身份。

## 本轮实际几何变更

v79 的主 GLB 含 **1,380 网格**。`V49_PHASEII_D1–D6_GRADE_MATCH_GROUND_LINK_INFERRED_NOT_BRIDGE` 六条来自 v48/v49 的 **未验证道路连接实体**，原 GIS layer 名含 `ACTIVE`，但属性已明确写明 *no verified OSM path alignment*。v79 的三角面重采样还证明宿舍到径向路原始模型存在约 18.58–20.62 模型米的平面空隙；此证据并不直接否定中央庭院道路的存在，只表明不能凭局部高程接近自行推断道路通达。

v80 **从主 GLB 移出这六个原有实体网格**（合计 448 个三角面），保留无损的 display-only GLB 和独立 GeoJSON/KML。完整可编辑主 GLB 由 1,380 → **1,374 网格**；其余 1,374 个网格的顶点、三角面索引、节点变换和可比较的顶点色均与 v79 完全一致。保留 v76 LRC 曲面天窗（与早期 v76 GLB 独立比较网格数据精确一致）。**没有新增或改写任何未实测的校园建筑、道路、玻璃窗格、树木、护栏或屋顶机房。**

2022 年 BNBU 官方施工航拍支持 D1–D6 六栋围绕中心场地的建筑组织，**不提供六条 V49 连接的道路中心线、宽度及入口标高**。因此六条仅作历史演示模型，不作为导航/道路拓扑/科学鸟撞暴露面积。

## 输出与 QA

- `model/BNBU_v80_ACCEPTED_NO_INFERRED_LINKS.glb`: **1,374 个活跃主网格**
- `model/BNBU_v80_V49_UNVERIFIED_LINKS_DISPLAY_ONLY.glb`: **6 个独立历史候选网格，448 面**
- `data/BNBU_v80_EDITABLE_GIS.gpkg`: **145 个 GIS 图层**，原 `v49_ACTIVE...` 转为 `v80_DISPLAY_ONLY...`，保留原几何并添加 `is_routable=0`、`is_surveyed=0`
- `data/BNBU_v80_ACTIVE.geojson`, `.kml`: **561 个活跃要素**；历史候选 6 个作为独立 display-only GeoJSON/KML
- `viewer/BNBU_Campus_3D_Offline_v80.html`: 改写 v78 的完整离线查看器内部 GLB 为 **v80 主 GLB 的原始 bytes 的 base64**，并同步内嵌有效 GIS 561 个要素；**无 CDN/相对 asset URL 依赖**
- `viewer/BNBU_v80_3D_Quarantine_Inspector.html`: 独立且无需 WebGL 的 Canvas 3D 源三角面查看器，默认不显示六条候选，勾选后叠加历史原面；可单独选 D1–D6，拖动旋转、滚轮缩放
- `qa/v80_geometry_change.json`, `v80_independent_validation.json`, `v80_small_viewer_browser.json`, `v80_Javascript_check.txt`, `SHA256_v80.json`
- `qa/BNBU_v80_actual_triangle_comparison.png`: 真实 GLB 三角面三维浏览器 before/after。

**结果**：v80 1374/6 网格原始顶点+面片+变换回读、v76 LRC skylight、GPKG 分层、GeoJSON/KML 全量排除、被转移原始六条路径的真实 GIS 轮廓一致、HTML 嵌入 GLB SHA256 **通过**。新建轻量 3D 查看器 Chromium 运行、默认隐藏、显示开关、建筑切换、零 JS 错误 **通过**。完整离线查看器 JS 语法 `node --check` 通过、嵌入资产结构验证通过；但本环境阻止 Chromium `file://` 访问，`set_content` 的完整 WebGL 渲染验证超时，**全校园可见渲染不声称通过**。完整源 HTML 仍沿用已验证的 v78 引擎，只换内嵌真实模型与 GIS。

## 重建

在本 ZIP 根目录：

```bash
pip install -r requirements.txt
python build_v80.py
python verify_v80.py
python make_v80_inspector.py
python test_small_viewer_v80.py
```

`input/` 包含直接 v79 父版本 GLB/GPKG/GeoJSON/KML 以及对应 v78 离线 viewer。历史 v10 检查点作为版本源文件保存在 `reference/`，不作重建输入。`qa/v79_*` 也保留了既有 47 热点、V52 12 个桥端、二期 12 段连接缺口真实三角面调查。

## 来源与精度

- 官方 2025 手绘校园图：<https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg>，仅限拓扑/形态参考。
- 官方 2022 二期六栋宿舍施工航拍：<https://www.bnbu.edu.cn/info/1078/13974.htm>，不能作为正射测量。
- 模型坐标：XY = EPSG:32649 UTM49N **减去 (758940, 2474080)**；Z 为相对模型高度，非真实 DEM、正高或相机测绘。
- GIS：EPSG:4326，继承旧 v79 的未测绘坐标标注。
- 在取得 OSM 原始 way/nodes、可复现正射配准、实测入口或道路中心线之前，**不得把 quarantined 连路重新计入主场景或路线图**。也不意味着证实不存在真实道路。

当前缺口：真实道路/入口观测、V52 桥端坡面对应、V60 东西水岸和完整 LRC 外斜撑逐照片配准、CTV 小房子名称尺寸、DEM/湖岸真实水位、窗玻璃逐面尺度。本版本不宣称解决这些缺口，也未发送邮件。