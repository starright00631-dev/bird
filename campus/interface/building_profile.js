import t1Profile from './t1_demo_profile.json';
import './building_profile.css';

export const profileBuildingId = t1Profile.building.id;

const modules = new Map(t1Profile.modules.map(module => [module.id, module]));
const sources = new Map(t1Profile.sources.map(source => [source.id, source]));
const listeners = new Set();
let selection = null;

export const getBuildingProfile = () => selection;
export function subscribeBuildingProfile(listener) {
 listeners.add(listener);
 return () => listeners.delete(listener);
}

export function setBuildingProfile(buildingId, moduleId = null) {
 const module = modules.get(moduleId) ?? null;
 if (buildingId !== profileBuildingId) {
  if (!selection) return;
  selection = null;
 } else {
  if (selection?.module === module) return;
  selection = {building: t1Profile.building, module};
 }
 for (const listener of listeners) listener();
}

export function selectBuildingProfileMesh(meshName) {
 const module = t1Profile.modules.find(entry => entry.mesh_names.includes(meshName));
 setBuildingProfile(module || meshName === t1Profile.building.anchor_node ? profileBuildingId : null, module?.id);
}

export function getBuildingModule(moduleId) {
 return modules.get(moduleId);
}

export function openBuildingProfile(moduleId = null) {
 document.dispatchEvent(new CustomEvent('bnbu-open-building-profile', {detail: {moduleId}}));
}

export function buildingFactText(fact) {
 const value = typeof fact.value === 'number' ? fact.value.toLocaleString('zh-CN') : fact.value;
 return fact.unit ? `${value} ${fact.unit}` : String(value);
}

export function buildingProfileAnswer(question, current, scene) {
 if (scene !== 'campus' || /实测|校准|碰撞率|鸟撞风险|概率|致死|多少次鸟撞|碰撞次数|改造效果/.test(question)) return null;
 if (!/\bT\s*1\b|厚德楼|工商管理楼/i.test(question) && (!current || !/这栋|当前|楼|连廊|连桥|立面|玻璃|临湖|屋面|哪面|观察|高度|面积|构件/.test(question))) return null;

 const topic = /连廊|连桥|T\s*2/i.test(question) ? /连廊|连桥/ :
  /玻璃|立面|临湖|哪面|观察/.test(question) ? /立面|临湖/ :
  /西北/.test(question) ? /西北/ : /东南/.test(question) ? /东南/ :
  /主楼|主翼|主楼层/.test(question) ? /主楼|主翼/ : null;
 const module = topic ? t1Profile.modules.find(entry => topic.test(entry.label)) :
  /概览|概况|介绍|整体/.test(question) ? null : current?.module;
 return {
  title: module ? `${t1Profile.building.label} · ${module.label}` : t1Profile.building.label,
  description: module?.description ?? t1Profile.building.description,
  facts: module?.facts ?? t1Profile.building.facts,
  moduleId: module?.id ?? null,
 };
}

function element(tag, content, className) {
 const node = document.createElement(tag);
 if (content) node.textContent = content;
 if (className) node.className = className;
 return node;
}

export function mountBuildingProfile(panel, onFocusModule) {
 const title = element('h3', t1Profile.building.label);
 const nav = element('div', null, 'building-profile-options');
 nav.setAttribute('role', 'group');
 nav.setAttribute('aria-label', '建筑构件');
 const buttons = [null, ...t1Profile.modules].map(module => {
  const button = element('button', module?.label ?? '概览', 'bp6-button bp6-small');
  button.type = 'button';
  button.addEventListener('click', () => onFocusModule(module?.id ?? null));
  nav.append(button);
  return {button, module};
 });
 const description = element('p', null, 'building-profile-description');
 const details = element('dl', null, 'building-profile-facts');
 const evidence = element('details', null, 'building-profile-sources');
 const list = element('ul');
 evidence.append(element('summary', '资料来源'), list);
 panel.append(title, nav, description, details, evidence);

 function render() {
  panel.hidden = !selection;
  if (!selection) return;
  for (const {button, module} of buttons) button.setAttribute('aria-pressed', String(module === selection.module));
  description.textContent = selection.module?.description ?? t1Profile.building.description ?? '';
  description.hidden = !description.textContent;
  const facts = selection.module?.facts ?? t1Profile.building.facts;
  details.replaceChildren(...facts.map(fact => {
   const entry = element('div');
   entry.append(element('dt', fact.label), element('dd', buildingFactText(fact)));
   return entry;
  }));
  const sourceIds = new Set(facts.flatMap(fact => fact.source_ids));
  list.replaceChildren(...Array.from(sourceIds, id => {
   const source = sources.get(id);
   const item = element('li');
   const label = element(source.url ? 'a' : 'strong', source.label);
   if (source.url) {
    label.href = source.url;
    label.target = '_blank';
    label.rel = 'noopener noreferrer';
   }
   item.append(label, element('p', source.description));
   return item;
  }));
 }
 subscribeBuildingProfile(render);
 render();
}
