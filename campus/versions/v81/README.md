# BNBU 珠海校园可编辑 GIS/3D · v81 (2026-11-12)

继承 **v80** 的原始模型，不从历史 v10 重做。此版是**实体三维证据分层的几何改动**，而非新增测绘成果：把原 v60 的 13 组桥柱（每组两根柱合为一个网格）与 13 道桥下横梁，以及 v54 一段由高程/端点推断的岸坡连接，共 **27 个非实测构件**从主 GLB 剥离为可独立加载的 `DISPLAY_ONLY` GLB。原 27 网格 **2476 个三角面**及局部坐标全部原样保存；真实地理位置、跨水连接、支撑数量没有凭空验证。桥面本体保留主模型（但 XY 也仍为未测绘代理）。

## 资料与归因

- [学校官方临湖校园照片](https://co.bnbu.edu.cn/en/images/banner2.jpg)：可见临水建筑与栈道，支持栈道及立柱**类型**，**不能验证柱子数量、间距、岸坡连接方向或桥台高度**。
- [学校 2025 手绘图](https://www.bnbu.edu.cn/en/images/shouhuiditu2025.jpg)：只作校园道路/桥/建筑**结构关系**参考，非正射影像。
- [RLP 设计方项目](https://rlp.asia/en/project/beijing-normal-university-hong-kong-baptist-university-united-international-college/)：确认连桥及错层组织设计逻辑，不提供逐桥点位测量。
- 源数据为 v80 GLB / GeoPackage/ GeoJSON / KML / HTML，直接沿用先前 v78 对 v76.1 主模型与 v76 天窗的安全合并结果。

## 实际三维差异（已重新解析 GLB 验证）

| 检查 | v80 | v81 |
|---|---:|---:|
| 主 GLB 网格 | 1374 | 1347 |
| 隔离但可编辑的 GLB 网格 | 0 | 27 |
| 被转移三角面 | 0 | 2476 |
| 主 GLB 原始结构未改变节点数 | 1374 | 1347 |
| 活跃 GeoJSON/KML 要素 | 561 | 534 |
| 待证 GeoJSON/KML | 6 (v49 previous) | 27 (v60/v54 new archive) |
| GPKG 图层 | 145 | 146 |

主场景所有 1347 个保留节点与源文件的顶点、面索引、变换、着色逐一比较；27 个 display-only 历史网格也同样对比，均无差异。保留 v76 LRC 天窗及 v60 栈道桥面。过去 v80 移出的 6 个 V49 道路保持隔离，其前一版归档信息在父版本工程中。

## 交付文件

- `model/BNBU_v81_FULL_EDITABLE.glb`：校园完整活跃三维场景
- `model/BNBU_v81_UNVERIFIED_PIER_STATIONS_AND_RAMP_DISPLAY_ONLY.glb`：27 个历史推定源网格，可单独编辑
- `data/BNBU_v81_EDITABLE_GIS.gpkg`：146 图层，拆分 v60 实体层与待证层
- `data/BNBU_v81_ACTIVE.geojson` 与 `BNBU_v81_ACTIVE.kml`：活跃 534 要素
- `data/BNBU_v81_DISPLAY_ONLY.geojson` 与 `.kml`：27 个历史待证要素
- `viewer/BNBU_Campus_3D_Offline_v81.html`：完整 1347 网格离线 Three.js 查看器（浏览器环境本轮阻止 WebGL 运行；代码/嵌入资产已核对）
- `viewer/BNBU_v81_Boardwalk_Source_Triangles_Inspector.html`：实源三角面三维 Canvas 查看器，Chromium 实测通过，27 待证构件默认隐藏。高度 ×8 仅是可关闭的显示选项
- `figures/BNBU_v81_actual_GLB_geometry_before_after.png`：真实原网格对应的对照图
- `qa/`：GLB 重载、GIS/KML/GPKG 和嵌入数据的完整独立检查、浏览器测试结果、SHA256 文件

## 可复现运行

```bash
pip install -r requirements.txt
python source/build_v81.py
python source/verify_v81.py
python source/make_v81_inspector.py
python source/browser_v81.py
python source/check_js_v81.py
```

构建脚本使用 `input/` 中父模型，而不是旧 v10。`reference/` 保留 v10 原压缩包、v79 连通性检测、v80 验证与构建代码供审查。

## 可信级别、几何误差与未解决项

GLB X/Y 使用 EPSG:32649 UTM49N 减 (758940,2474080)，所有 Z 都是模型局部相对值，**不是测绘高程**。GeoJSON/KML/GPKG 为 EPSG:4326，继承的点位未与正射图注册。照片类型证据与每个网格实测位置是两回事。没有新增 OSM way、COLMAP 注册、湖底 DEM、桥端实测或玻璃几何。不能用于通行路线或鸟撞面积/风险分母。此前删除的 690 假玻璃带、6 护栏、5 机房保持不恢复，没有随机窗、树、路或桥。

全校园 WebGL 的真实运行仍受当前 Chromium 的文件/localhost 访问策略限制；不能当作已通过。相对独立的局部 Canvas 三维观察器通过了实际 Chromium 测试，含轨道旋转、显示切换及可追踪的原始三角面。