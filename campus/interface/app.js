import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const ROOT = './';
const TYPES = [
 ['terrain_unsurveyed','山体 / 地势','#76a06d'],
 ['water_unsurveyed','湖泊水面','#4cafd9'],
 ['shore_unsurveyed','湖岸与坡面','#d5b278'],
 ['vehicle_roads_unsurveyed','车行道路','#e1a091'],
 ['pedestrian_paving_unsurveyed','步行路面 / 铺装','#cfbd9c'],
 ['ground_connectors_unsurveyed','地面连接（非桥）','#c99fd7'],
 ['elevated_boardwalk_unsurveyed','临水廊道与支柱','#9ca5e2'],
 ['stairs_unsurveyed','楼梯','#d7ac92'],
 ['glass_proxies_unregistered','玻璃候选面','#68d2c1'],
 ['architecture_opaque','建筑与实体墙','#bdc8d3']
];
const names = Object.fromEntries(TYPES.map(t=>[t[0],t[1]]));
const colors = Object.fromEntries(TYPES.map(t=>[t[0],t[2]]));
const $ = id=>document.getElementById(id);
const progress = text => { $('scene-status').textContent=text; $('health').textContent=text; };
const esc = str => String(str??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const reader = new GLTFLoader();
const embed = key => $('embedded-'+key);
const isStandalone = !!embed('v66');

async function loadBinary(key,rel){
 const script=embed(key);
 if(script){
  const raw=atob(script.textContent.replace(/\s+/g,''));
  const bytes=new Uint8Array(raw.length);
  for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);
  return bytes.buffer;
 }
 const response=await fetch(ROOT+rel);
 if(!response.ok)throw new Error('文件缺失 '+rel+' (HTTP '+response.status+')');
 return response.arrayBuffer();
}
async function loadJson(key,rel){
 const script=embed(key);
 if(script)return JSON.parse(script.textContent);
 const response=await fetch(ROOT+rel);
 if(!response.ok)throw new Error('GIS 文件缺失 '+rel+' (HTTP '+response.status+')');
 return response.json();
}
async function loadScene(key,path){
 const data=await loadBinary(key,path);
 return await new Promise((resolve,reject)=>reader.parse(data,'',resolve,reject));
}

const host=$('scene3d');
let renderer;
try{
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
 renderer.setPixelRatio(Math.min(2,window.devicePixelRatio||1));
 renderer.setClearColor(0xd0e1e8,1);
 renderer.outputColorSpace=THREE.SRGBColorSpace;
 renderer.toneMapping=THREE.ACESFilmicToneMapping;
 renderer.toneMappingExposure=1.32;
 host.append(renderer.domElement);
}catch(err){
 $('render-error').hidden=false;
 $('render-error').textContent='浏览器无法初始化 WebGL。请更新显卡驱动，并使用新版 Chrome / Edge。详细原因：'+String(err);
 throw err;
}
const scene=new THREE.Scene();
scene.background=new THREE.Color(0xcddfe7);
const cam=new THREE.PerspectiveCamera(47,1,.05,50000);
scene.add(new THREE.HemisphereLight(0xffffff,0x6b8a9b,2.8));
const sun=new THREE.DirectionalLight(0xffffff,2.1);sun.position.set(300,650,180);scene.add(sun);
const orbit=new OrbitControls(cam,renderer.domElement);orbit.enableDamping=true;orbit.dampingFactor=.08;orbit.minDistance=1;
let campus=null,dsm=null,current='campus',activeRoot=null;
let meshes=[],groups=new Map(),gis=null,contours=null,dsmMeta=null,featuresByName=new Map();
const visible=new Set(TYPES.map(t=>t[0]));
let selectedName=null,outline=null,viewStatus='loading';
const boxWorld=obj=>new THREE.Box3().setFromObject(obj);
function fit(box,top=false){
 if(!box || box.isEmpty())return;
 const size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
 const length=Math.max(size.x,size.z,30),height=Math.max(size.y,4);
 const radius=Math.max(length*1.45,Math.max(height*3,60));
 orbit.target.copy(center);
 if(top){
  cam.up.set(0,0,-1);
  cam.position.set(center.x,center.y+radius*1.6,center.z);
 }else{
  cam.up.set(0,1,0);
  cam.position.set(center.x+radius*.72,center.y+radius*.8,center.z+radius*.7);
 }
 cam.near=Math.max(.02,radius/40000);cam.far=Math.max(3000,radius*45);
 cam.updateProjectionMatrix();cam.lookAt(center);orbit.update();
}
const allBox=()=>activeRoot?boxWorld(activeRoot):null;
function tag(mesh){
 let p=mesh.parent;
 while(p && p!==campus){
  if(p.userData?.layer)return p.userData.layer;
  const prefix='BNBU_GROUP_';
  if(p.name && p.name.startsWith(prefix))return p.name.slice(prefix.length).toLowerCase();
  p=p.parent;
 }
 return 'architecture_opaque';
}
function indexCampus(){
 campus.updateMatrixWorld(true);
 meshes=[];
 groups.clear();
 campus.traverse(obj=>{
  if(obj.name?.startsWith('BNBU_GROUP_')){
   const key=obj.userData?.layer || obj.name.slice('BNBU_GROUP_'.length).toLowerCase();
   groups.set(key,obj);
  }
  if(obj.isMesh){obj.userData.bnbuCategory=tag(obj);meshes.push(obj);}
 });
 if(meshes.length!==1377)throw new Error('场景数据完整性检查失败：预期 1377 个网格，读取到 '+meshes.length);
 for(const mesh of meshes){
  if(mesh.material){const list=Array.isArray(mesh.material)?mesh.material:[mesh.material];
   for(const mat of list){mat.side=THREE.DoubleSide;}
  }
 }
 renderLayerControls();
}

function renderLayerControls(){
 const target=$('layers');target.textContent='';
 for(const [key,label,color] of TYPES){
  const group=groups.get(key);
  const count=group?group.children.filter(x=>x.isMesh).length:0;
  const el=document.createElement('div');el.className='layer-item';
  const id='part-'+key;
  el.innerHTML='<input id="'+id+'" type="checkbox" '+(visible.has(key)?'checked':'')+'><i class="color-dot" style="background:'+color+'"></i><label for="'+id+'">'+label+'</label><span class="count">'+count+'</span><button type="button" class="focus" data-part="'+key+'">定位</button>';
  const c=el.querySelector('input');c.addEventListener('change',()=>toggleLayer(key,c.checked));
  el.querySelector('button').addEventListener('click',()=>focusGroup(key));
  target.append(el);
 }
}
function toggleLayer(key,on){
 if(on)visible.add(key);else visible.delete(key);
 const group=groups.get(key);if(group)group.visible=on;
 redraw();
}
$('show-all').addEventListener('click',()=>{for(const [key] of TYPES)visible.add(key);for(const g of groups.values())g.visible=true;renderLayerControls();redraw();});
$('hide-all').addEventListener('click',()=>{visible.clear();for(const g of groups.values())g.visible=false;renderLayerControls();redraw();});

function focusGroup(key){
 if(current!=='campus')return;
 const g=groups.get(key);
 if(g){if(!g.visible){toggleLayer(key,true);renderLayerControls();}fit(boxWorld(g));}
}
function focusPreset(key){
 if(current==='dsm'){fit(allBox(),key==='all');return;}
 if(!campus)return;
 if(key==='all'){fit(allBox());return;}
 if(key==='lake'){focusGroup('water_unsurveyed');return;}
 if(key==='ridge'){focusGroup('terrain_unsurveyed');return;}
 if(key==='roads'){focusGroup('vehicle_roads_unsurveyed');return;}
 if(key==='boardwalk'){focusGroup('elevated_boardwalk_unsurveyed');return;}
 let subset=[];
 if(key==='cc')subset=meshes.filter(m=>/(^MAIN_CC$|^ROOF_(DECK|PARAPET)_CC$|STORYEDGE_CC_|_CC_)/i.test(m.name));
 if(key==='phase1'||key==='phase2'){
  // Actual geometric world-space bounding centres, NOT node origins (all original meshes use shared origin).
  subset=meshes.filter(m=>{const c=boxWorld(m).getCenter(new THREE.Vector3());return (key==='phase2') === (c.z < -500);});
 }
 if(!subset.length){progress('所选区域暂无可信的独立网格定位记录');return;}
 const box=new THREE.Box3();subset.forEach(m=>box.union(boxWorld(m)));fit(box);
}
document.querySelectorAll('[data-focus]').forEach(b=>b.addEventListener('click',()=>focusPreset(b.dataset.focus)));
$('reset-view').addEventListener('click',()=>fit(allBox()));
$('top-view').addEventListener('click',()=>fit(allBox(),true));

function updateSceneVisibility(){
 if(campus)campus.visible=current==='campus';
 if(dsm)dsm.visible=current==='dsm';
 for(const b of document.querySelectorAll('[data-focus]'))b.disabled=current==='dsm'&&b.dataset.focus!=='all';
 $('choose-campus').classList.toggle('selected',current==='campus');
 $('choose-dsm').classList.toggle('selected',current==='dsm');
 $('layers').parentElement.style.display=current==='campus'?'':'none';
 $('map-section').querySelector('.map-top strong').textContent=current==='campus'?'校园 GIS 轮廓':'DSM 10 米等高线';
}
async function switchScene(which){
 if(which===current&&activeRoot)return;
 current=which;
 updateSceneVisibility();
 if(which==='campus'){
  if(!campus)await ensureCampus();
  activeRoot=campus;updateSceneVisibility();fit(allBox());
  progress('校园三维已就绪 · '+meshes.length+' 个网格');
 }else{
  if(!dsm)await ensureDSM();
  activeRoot=dsm;updateSceneVisibility();fit(allBox());
  progress('ALOS DSM 已就绪 · 约 30 米格网 · 与建筑分离');
 }
 redraw();
}
$('choose-campus').addEventListener('click',()=>switchScene('campus').catch(showError));
$('choose-dsm').addEventListener('click',()=>switchScene('dsm').catch(showError));

async function ensureCampus(){
 progress('读取完整校园网格…');
 const gltf=await loadScene('v66','generated/BNBU_v66_SEMANTIC_Y_UP.glb');
 campus=gltf.scene;scene.add(campus);indexCampus();campus.visible=current==='campus';
 for(const [key,g] of groups)g.visible=visible.has(key);
}
async function ensureDSM(){
 progress('读取遥感地形参考…');
 const gltf=await loadScene('dsm','generated/BNBU_v67_OBSERVED_ALOS_DSM_SEPARATE.glb');
 dsm=gltf.scene;scene.add(dsm);
 dsm.visible=current==='dsm';
 dsmMeta=await loadJson('dsm-meta','generated/BNBU_v67_TERRAIN_SOURCE_AND_LIMITS.json');
 try{contours=await loadJson('contours','generated/BNBU_v67_AW3D30_CONTOURS_INTERPOLATED.geojson');}catch(e){console.warn('DSM contour unavailable',e);}
}
async function ensureGIS(){
 try{
  gis=await loadJson('gis','generated/BNBU_v66_RESOLVED_REFERENCES.geojson');
  if(!Array.isArray(gis.features)||gis.features.length!==522)throw new Error('预期522条GIS记录');
  for(const f of gis.features){
   const n=f.properties?.render_model_node;
   if(n){const matches=featuresByName.get(n)||[];matches.push(f);featuresByName.set(n,matches);}
  }
  computeMapBounds();redraw();
 }catch(e){console.error(e);$('map-section').querySelector('.map-footnote').textContent='GIS 轮廓资源加载失败：'+e.message;}
}
function showError(e){
 console.error(e);viewStatus='error';
 const el=$('render-error');el.hidden=false;
 el.textContent='加载失败：'+(e.message||e)+'。请用 ZIP 中的「双击查看_校园3D.html」，或运行「启动查看器.bat」。';
 progress('模型加载失败');
 window.__BNBU_READY__=false;
}
function clearOutline(){
 if(outline){scene.remove(outline);outline.geometry?.dispose?.();outline.material?.dispose?.();outline=null;}
}
function selectMesh(mesh,position=null){
 if(!mesh)return;
 selectedName=mesh.name;clearOutline();
 const b=boxWorld(mesh);outline=new THREE.Box3Helper(b,0x00e6e5);scene.add(outline);
 const matches=featuresByName.get(mesh.name)||[];
 const p=matches[0]?.properties||{};
 const source=p.source||p.geometry_basis||'既有模型，未找到单独测绘证据';
 const confidence=p.confidence||p.confidence_geometry||'尚未实测确认';
 const text='<strong>'+esc(mesh.name)+'</strong><div class="kv">图层：'+esc(names[mesh.userData.bnbuCategory]||'遥感高程')+'</div><div class="kv">GIS 关联：'+matches.length+' 条</div><div class="kv">来源：'+esc(source)+'</div><div class="kv">置信状态：'+esc(confidence)+'</div>';
 $('selection').innerHTML=text;$('match-count').textContent=matches.length+' 项关联';
 redraw();
}
const raycaster=new THREE.Raycaster(),point=new THREE.Vector2();
let mousedownPos=null;
renderer.domElement.addEventListener('pointerdown',e=>{mousedownPos=[e.clientX,e.clientY];});
renderer.domElement.addEventListener('pointerup',event=>{
 if(!activeRoot||!mousedownPos)return;
 const drift=Math.hypot(event.clientX-mousedownPos[0],event.clientY-mousedownPos[1]);mousedownPos=null;
 if(drift>5)return;
 const r=renderer.domElement.getBoundingClientRect();point.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);
 raycaster.setFromCamera(point,cam);
 const targets=current==='campus'?meshes.filter(m=>m.visible&&m.parent?.visible):dsm?.children||[];
 const hits=raycaster.intersectObjects(targets,true);
 if(!hits.length)return;
 if(current==='campus')selectMesh(hits[0].object);
 else{
  const hit=hits[0].point;
  $('selection').innerHTML='<strong>ALOS DSM 插值曲面</strong><div class="kv">表面高程 ≈ '+hit.y.toFixed(1)+' 米（像元间插值，非地面实测）</div><div class="kv">本场景未与建筑模型标高配准</div>';
 }
});

const canvas=$('map2d'),ctx=canvas.getContext('2d');
let mapScale=1,mapPan=[0,0],geoExtent=null,mapDragging=null;
function walkCoordinates(obj,fn){
 if(!Array.isArray(obj))return;
 if(obj.length>=2&&typeof obj[0]==='number'&&typeof obj[1]==='number'){fn(obj);return;}
 for(const child of obj)walkCoordinates(child,fn);
}
function computeMapBounds(){
 if(!gis)return;let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
 for(const f of gis.features)walkCoordinates(f.geometry?.coordinates,p=>{minX=Math.min(minX,p[0]);maxX=Math.max(maxX,p[0]);minY=Math.min(minY,p[1]);maxY=Math.max(maxY,p[1]);});
 geoExtent={minX,maxX,minY,maxY,mx:(minX+maxX)/2,my:(minY+maxY)/2};
}
function geoClass(f){
 const p=f.properties||{},name=(p.render_model_node||p.model_node||'').toUpperCase();
 if(p.feature_type==='terrain_relief'||name.includes('TERRAIN_RELIEF'))return 'terrain_unsurveyed';
 if(p.role==='water_existing_v44_not_surveyed'||name.startsWith('LAKE_'))return 'water_unsurveyed';
 if(p.role==='shore_existing_v44_not_surveyed'||name.startsWith('SHORE_'))return 'shore_unsurveyed';
 if(p.role==='vehicle_road')return 'vehicle_roads_unsurveyed';
 if(p.role==='footpath'||p.role==='phaseII_walk_pavement')return 'pedestrian_paving_unsurveyed';
 if(name.includes('GRADE_MATCH_GROUND_LINK'))return 'ground_connectors_unsurveyed';
 if(name.includes('BOARDWALK'))return 'elevated_boardwalk_unsurveyed';
 if(name.includes('STAIR'))return 'stairs_unsurveyed';
 if(name.includes('GLASS')&&!name.includes('OPAQUE'))return 'glass_proxies_unregistered';
 return 'architecture_opaque';
}
function geomPaths(geom){
 const result=[];if(!geom)return result;
 const {type,coordinates:c}=geom;
 if(type==='Point')return [[c]];
 if(type==='LineString'||type==='MultiPoint')return [c];
 if(type==='Polygon'||type==='MultiLineString')return c;
 if(type==='MultiPolygon')return c.flat(1);
 return result;
}
function drawMap(){
 const rect=canvas.getBoundingClientRect(),w=rect.width,h=rect.height;
 if(w<1||h<1)return;
 const ratio=Math.min(2,window.devicePixelRatio||1);
 canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);
 ctx.setTransform(ratio,0,0,ratio,0,0);
 ctx.fillStyle='#142739';ctx.fillRect(0,0,w,h);
 ctx.strokeStyle='#22374b';ctx.lineWidth=.8;
 for(let x=0;x<w;x+=34){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
 for(let y=0;y<h;y+=34){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
 if(!geoExtent){ctx.fillStyle='#7c9bad';ctx.fillText('正在读取 GIS 坐标…',12,22);return;}
 const cos=Math.cos(geoExtent.my*Math.PI/180);
 const dx=(geoExtent.maxX-geoExtent.minX)*cos,dy=geoExtent.maxY-geoExtent.minY;
 const base=Math.min((w-34)/dx,(h-34)/dy);
 const project=p=>[w/2+(p[0]-geoExtent.mx)*cos*base*mapScale+mapPan[0],
                   h/2-(p[1]-geoExtent.my)*base*mapScale+mapPan[1]];
 const entries=current==='dsm'?(contours?.features||[]):gis.features;
 for(const f of entries){
  const key=current==='dsm'?'shore_unsurveyed':geoClass(f);
  if(current==='campus'&&!visible.has(key))continue;
  const selected=current==='campus'&&f.properties?.render_model_node===selectedName;
  ctx.strokeStyle=selected?'#27ffff':current==='dsm'?'#f7cc80':colors[key];
  ctx.lineWidth=selected?2.3:current==='dsm'?0.8:.75;
  ctx.globalAlpha=selected?1:.75;
  for(const path of geomPaths(f.geometry)){
   if(!path?.length)continue;
   ctx.beginPath();
   for(let k=0;k<path.length;k++){const [x,y]=project(path[k]);if(k===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}
   if(f.geometry.type.includes('Polygon')){ctx.closePath();ctx.fillStyle=selected?'#5adbd9':'#7ea2b7';ctx.globalAlpha=selected?.27:.07;ctx.fill();ctx.globalAlpha=selected?1:.75;}
   ctx.stroke();
  }
 }
 ctx.globalAlpha=1;
 ctx.fillStyle='#b9d1e0';ctx.font='10px system-ui';
 ctx.fillText(current==='campus'?'522 条原模型 GIS 记录':'ALOS 30m DSM 推算等高线',10,h-10);
}
function redraw(){requestAnimationFrame(drawMap);}
function changeZoom(factor){mapScale=Math.max(.3,Math.min(22,mapScale*factor));redraw();}
$('map-fit').onclick=()=>{mapScale=1;mapPan=[0,0];redraw();};
$('map-zoom-in').onclick=()=>changeZoom(1.4);
$('map-zoom-out').onclick=()=>changeZoom(1/1.4);
canvas.addEventListener('pointerdown',e=>{mapDragging=[e.clientX,e.clientY,mapPan[0],mapPan[1]];canvas.setPointerCapture(e.pointerId);canvas.style.cursor='grabbing';});
canvas.addEventListener('pointermove',e=>{if(!mapDragging)return;mapPan=[mapDragging[2]+e.clientX-mapDragging[0],mapDragging[3]+e.clientY-mapDragging[1]];redraw();});
canvas.addEventListener('pointerup',()=>{mapDragging=null;canvas.style.cursor='grab';});
canvas.addEventListener('pointercancel',()=>{mapDragging=null;canvas.style.cursor='grab';});
canvas.addEventListener('wheel',e=>{e.preventDefault();changeZoom(e.deltaY<0?1.12:1/1.12);},{passive:false});
new ResizeObserver(()=>{const r=host.getBoundingClientRect();if(r.width>0&&r.height>0){cam.aspect=r.width/r.height;cam.updateProjectionMatrix();renderer.setSize(r.width,r.height);}redraw();}).observe(host);
new ResizeObserver(redraw).observe(canvas);
$('tab-map').onclick=()=>{$('tab-map').classList.add('active');$('tab-source').classList.remove('active');$('map-section').hidden=false;$('source-section').hidden=true;redraw();};
$('tab-source').onclick=()=>{$('tab-source').classList.add('active');$('tab-map').classList.remove('active');$('map-section').hidden=true;$('source-section').hidden=false;};
$('help-button').onclick=()=>$('help-dialog').showModal();
$('close-help').onclick=()=>$('help-dialog').close();
function animate(){requestAnimationFrame(animate);orbit.update();renderer.render(scene,cam);}
animate();
async function start(){
 try{
  // First put actual geometry on screen. GIS is optional: failure must not blank 3D.
  await switchScene('campus');
  window.__BNBU_READY__=true;
  window.__BNBU_VERSION__='v68';
  window.__BNBU_DEBUG__={getScene:()=>current,meshCount:()=>meshes.length,layerCount:()=>groups.size,hasGIS:()=>!!gis,hasDSM:()=>!!dsm,layerVisible:k=>groups.get(k)?.visible};
  ensureGIS();
 }catch(e){showError(e);}
}
start();
