# BNBU 校园可编辑 GIS / 3D v75（2026-11-12）

## 本轮真实修改，不以报告替代模型

本工程**直接继承 v64 的全部已保留建筑、道路、湖泊及四组山体网格**，并比对 Library 内更新的 `BNBU_Campus_Full_v74.zip` 与其 v71/v74 几何来源。按用户要求重新检查最早的 `BNBU_hourly_campus_v10_2026-11-10.zip`，读取 `enhance_v10.py`、历史 GLB、GPKG 及 `v10_model_assertions.json`，未重新生成校园。

1. **37 组原有不透明楼层边饰变成真正封闭的独立三维体**。包括 T1、T2、T3、演艺厅及 V15/V17/V19/V21/V23/V27 原有层带。早期版本在带状内环与外环共用一个点处存在非流形/开放三角面；采用沿原上表面轮廓 0.5 毫米模型级消除数学切点，再重新生成底面与侧壁。原楼层 top/bottom Z、颜色、建筑身份与整体形状不变。没有新增玻璃或楼层数。共 1,924 个新网格三角面，累计原上表面面积 2,210.172 模型平方米（**跨楼层累计面积，不是建筑占地面积，更非测量建筑面积**）。最大平面几何对称差 0.0000165 模型平方米，所有 37 个重建体通过回读后的 watertight、winding、正体积检查。
2. **合并 v74 历史中已研究的 2 处 LRC 湖边既有铺装缺口**。直接导入 `BNBU_v71_CONNECTED_LAKEFRONT.glb` 中两个约 4.156/4.247 模型平方米的封闭拼接构件，并发现其原网格 winding 不一致且 signed volume 为负；仅修复三角面法线朝向，不变动一个顶点。仍然属于旧模型同高铺装的**低可信接缝候选**，不作为测绘通路，也不自动加入可导航图。查看器**默认隐藏**两个候选，提供单独显隐。
3. **将 CTV/CC401 小屋等 4 个未经测绘的猜测构件从主 GLB 隔离**，并从活动 GIS 移去相关 5 个要素 / 2 个专属 GPKG 图层。原样保存在 `model/BNBU_v75_QUARANTINED_CTV_NOT_SURVEYED.glb` 和 `data/BNBU_v75_QUARANTINED_CTV_NOT_SURVEYED.geojson`，不丢失历史候选，直到获得确证照片与位置、大小、车道道路方式证据后才可回并。
4. **保留 v64 对四处旧山体的实际三维网格编辑**，不把来自 v74 的外部 ALOS AW3D30 约 30 m DSM 硬融合到相对 Z 模型。该独立 DSM 与其原始出处/局限已收在 `reference/`，供后续垂直控制点配准使用。

没有添加以前被删除的 **690 个无来源窗带、6 个未经确证玻璃护栏、5 个屋顶机房**，没有随机窗户、随机树木或猜测天窗。

## 交付与浏览

| 文件 | 用途 |
| --- | --- |
| `model/BNBU_v75_FULL_EDITABLE.glb` | 全校园 1,379 个独立模型节点，新增/删除/重建均体现在实际 GLB |
| `data/BNBU_v75_EDITABLE_GIS.gpkg` | 141 个可编辑图层，包括本轮 37 个修复构件和 2 个来源独立的小铺装接缝 |
| `data/BNBU_v75_ACTIVE.geojson`、`data/BNBU_v75_ACTIVE.kml` | 565 个当前活动矢量要素 / 地标（含非测绘声明） |
| `BNBU_Campus_3D_Viewer_v75.html` | 单个 HTML，无需 CDN，内嵌完整 GLB，附 v64 对照；已通过 JS 语法检查，完整运行时浏览器渲染在本执行环境未被验证 |
| `BNBU_v75_Changes_3D_Viewer.html` | 42 网格可操作小型查看器（37 个修复、2 个接缝、3 个原有 LRC 参照板），已完成 Chromium 真实加载/显隐测试 |
| `figures/BNBU_v75_actual_GLB_before_after.png` | 由 v64/v75 实际三角面绘制的建筑带、LRC 拼接、小屋隔离对照，不是航拍 |
| `figures/BNBU_v75_42mesh_browser.png` | Chromium 实际变化子场景截图 |
| `qa/` | 回读独立验证、来源限制、浏览器检查、SHA-256 |

`input/` 提供 v64 与 v71 所需源文件，`reference/` 包含 v10 原型核对资料及 v74 AW3D30 独立 DSM，可不依赖旧聊天重复构建。

运行：

```bash
python -m pip install numpy trimesh shapely scipy fiona pyproj matplotlib playwright
python source/build_v75.py
python source/verify_v75.py
python source/render_v75.py
python source/make_viewer_v75.py
python source/make_delta_viewer_v75.py
python source/test_delta_viewer_v75.py
```

浏览器测试只对完整查看器进行了 JS 语法校验与模型独立 GLB 解析；本容器中的 Chromium **禁止本地/localhost 导航**且 36 MB 文本注入运行超时，不将其冒充已通过完整硬件 WebGL 测试。42 个重点网格的较小浏览器查看器已真实加载，37+2 显隐差额均验证成功。

## 可信来源与坐标

- 官方 2025 手绘校园结构图：<https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg>，**仅做空间组织与类别结构约束，非正射图、非坐标或标高来源**。
- RLP 一期设计资料：<https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/>，只支持建筑/连廊设计语境。
- 岸边照片参考：<https://co.bnbu.edu.cn/en/info/1131/2702.htm>，只支持铺装类型，不支持源模型接岸位置的 0.5 米级估计。
- v74 中独立 AW3D30 派生参考来自 `https://terrain.ardupilot.org/SRTM1/N22E113.hgt.zip`，**DSM 含建筑植被，不是裸地 DEM；高程与模型相对 Z 尚未配准**。
- **GLB 水平坐标**：EPSG:32649 UTM Easting/Northing 减 `(758940, 2474080)`，Z 为 **模型相对数值**，不是测量高程。**GIS**：EPSG:4326。所有新增 GIS feature 明确 `is_surveyed=0, is_glass=0, is_routable=0, metric_birdstrike_eligible=0`。

**仍缺**：一/二期屋顶和玻璃逐面摄影测量、正射控制点、实际道路 OSM/Overpass way 节点和可信路宽、山体裸地 DEM、湖底高程/岸线和垂直坐标系统。不能以现模型直接推断精确通行距离、建筑玻璃暴露面积或鸟撞概率。

本工程既没有发送邮件，也不附加任何经过推断的建筑名称或新的假玻璃。