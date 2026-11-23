// The detail pane and chat read this same selection and evidence contract.
const identityFields = ['pane_id', 'building_id', 'facade_id', 'model_version'];
const evidenceTiers = new Set(['measured', 'local_survey', 'field_study', 'controlled_experiment', 'observational', 'remote_sensing', 'proxy', 'assumption', 'unknown']);
const states = new Set(['observed', 'inferred', 'conflict', 'missing', 'withheld']);
const names = {
 optical_mechanism: '反射或透视表现',
 exterior_vlr: '外表面可见光反射率',
 exterior_vlt: '外表面可见光透射率',
 reflected_vegetation: '窗内植被倒影占比',
 tree_cover_0_5_m: '0–5 m 树冠覆盖率',
 tree_cover_5_25_m: '5–25 m 树冠覆盖率',
 tree_cover_25_100_m: '25–100 m 树冠覆盖率',
 tree_cover_100_1000_m: '100 m–1 km 树冠覆盖率',
 tree_cover_1000_10000_m: '1–10 km 树冠覆盖率',
 approach_count: '已标注接近事件',
 glass_contact_risk: '每次接近的玻璃接触风险',
 carcass_detection_risk: '每次有效巡查的检出风险',
 local_treatment_effect: '本地措施效果',
};
const withheld = new Set(['glass_contact_risk', 'carcass_detection_risk', 'local_treatment_effect']);
const ratios = new Set(Object.keys(names).filter(key => key === 'reflected_vegetation' || key.startsWith('tree_cover_')));
const percentages = new Set(['exterior_vlr', 'exterior_vlt']);
const optics = {reflection:'反射', transmission:'透视', both:'反射与透视',
 transparent:'透明', reflective:'反射', mirrored:'镜面反射',
 reflective_and_transparent:'反射与透视', frosted_translucent:'半透', opaque_spandrel:'不透明'};
const stateText = {observed:'实证', inferred:'推断', conflict:'来源冲突', missing:'缺少证据', stale:'已过期', withheld:'暂不提供结论'};
const token = value => typeof value === 'string' && value.trim() === value && value.length > 0 && value.length <= 180;
const timestamp = value => typeof value === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));
const sha256 = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const plain = value => value && typeof value === 'object' && !Array.isArray(value);
function assert(condition, message) { if (!condition) throw Error(message); }
function factType(id) {
 if (typeof id==='string' && id.startsWith('reflected_vegetation:')) return 'reflected_vegetation';
 return id;
}
function sources(values) {
 assert(Array.isArray(values) && values.length <= 120 && values.every(token), '无效来源 ID');
 return [...new Set(values)];
}

function parseFact(row) {
 assert(plain(row) && token(row.id) && Object.hasOwn(names,factType(row.id)) && states.has(row.status) && evidenceTiers.has(row.evidence_tier), '无效的证据事实');
 const {id, status, value, unit, observed_at, expires_at, evidence_tier, view_id=null} = row;
 const type=factType(id);
 assert(id === type ? view_id === null : token(view_id) && id === type+':'+encodeURIComponent(view_id), '倒影视角标识不匹配');
 const source_ids = sources(row.source_ids);
 assert(!withheld.has(id) || status === 'withheld', '本地结论必须等待相应现场验证');
 const expectedUnit = percentages.has(type) ? '%' : ratios.has(type) ? 'fraction' : id === 'approach_count' ? 'count' : null;
 assert(unit === expectedUnit, '证据单位不匹配');
 assert((observed_at === null || timestamp(observed_at)) && (expires_at === null || timestamp(expires_at)), '日期必须带时区');
 if (expires_at && observed_at) assert(Date.parse(expires_at) >= Date.parse(observed_at), '证据过期时间无效');
 if (status === 'observed' || status === 'inferred') {
  assert(!withheld.has(id) && observed_at && source_ids.length && evidence_tier !== 'unknown', '缺少结论、日期或证据来源');
  const validValue = id === 'optical_mechanism' ? typeof value === 'string' && Object.hasOwn(optics,value)
   : Number.isFinite(value) && value >= 0 && (id === 'approach_count' ? Number.isSafeInteger(value) : value <= (percentages.has(type) ? 100 : 1));
  assert(validValue, '证据取值越界');
 } else {
  assert(value === null, '缺失、冲突或待验证的事实必须保留空值');
  if (status === 'conflict') assert(source_ids.length >= 2, '冲突需要至少两个来源');
 }
 return {id, status, value, unit, observed_at, expires_at, evidence_tier, source_ids, view_id};
}

export function parsePaneEvidence(raw, sceneVersion, meshNames, meshRegistration = new Map()) {
 assert(plain(raw) && raw.schema_version === 1 && raw.scene_version === sceneVersion, '证据版本与当前 3D 场景不匹配');
 assert(['field','synthetic'].includes(raw.dataset_kind) && token(raw.evidence_snapshot_id)
  && sha256(raw.report_sha256) && timestamp(raw.valid_until) && Array.isArray(raw.bindings), '无效的证据包');
 assert(plain(raw.input_sha256) && ['registry','mapping','vegetation','glass'].every(key=>sha256(raw.input_sha256[key])),
  '缺少证据输入的校验值');
 const seenPanes = new Set(), bindings = new Map();
 for (const row of raw.bindings) {
  assert(plain(row) && token(row.object_name) && meshNames.get(row.object_name) === 1, '窗片绑定的 3D 对象不存在或名称重复');
  assert(plain(row.pane) && identityFields.every(field => token(row.pane[field]))
   && token(row.floor) && token(row.bay) && token(row.mapping_source_id), '窗片映射缺少定位和来源');
  const pane = Object.fromEntries(identityFields.map(key => [key,row.pane[key]]));
  if (raw.dataset_kind === 'field') {
   const registered = meshRegistration.get(row.object_name);
   assert(registered && identityFields.every(field => registered[field] === pane[field]),
    '实测窗片要求 3D 网格携带相同的窗片注册信息');
  }
  assert(!bindings.has(row.object_name) && !seenPanes.has(pane.pane_id), '窗片与 3D 对象须一一对应');
  assert(Array.isArray(row.facts), '缺少窗片事实表');
  const facts = row.facts.map(parseFact);
  const factIds = new Set(facts.map(fact => fact.id));
  assert(factIds.size === facts.length && [...withheld].every(id => factIds.has(id)), '事实重复或缺少待验证结论');
  seenPanes.add(pane.pane_id);
  bindings.set(row.object_name, {pane, floor:row.floor, bay:row.bay, mapping_source_id:row.mapping_source_id, facts});
 }
 return {
  schema_version:1, scene_version:sceneVersion, evidence_snapshot_id:raw.evidence_snapshot_id,
  dataset_kind:raw.dataset_kind, report_sha256:raw.report_sha256, valid_until:raw.valid_until, bindings,
  input_sha256:Object.fromEntries(['registry','mapping','vegetation','glass'].map(key=>[key,raw.input_sha256[key]])),
 };
}

export function buildContext(selection, bundle = null, now = Date.now()) {
 const object = selection.object_name ?? null;
 const generic = {scene:selection.scene, object_name:object, status:selection.status};
 const binding = selection.scene === 'campus' && bundle?.bindings.get(object);
 if (!binding) return generic;
 const expired = Date.parse(bundle.valid_until) <= now;
 const facts = binding.facts.map(fact =>
  (expired || (fact.expires_at && Date.parse(fact.expires_at) <= now))
    && (fact.status === 'observed' || fact.status === 'inferred')
   ? {...fact, status:'stale', value:null}
   : fact);
 return {
  ...generic, status:expired ? 'stale' : bundle.dataset_kind === 'field' ? 'field_registered' : 'synthetic',
  schema_version:bundle.schema_version, scene_version:bundle.scene_version,
  evidence_snapshot_id:bundle.evidence_snapshot_id, report_sha256:bundle.report_sha256, input_sha256:bundle.input_sha256,
  pane:binding.pane, floor:binding.floor, bay:binding.bay, mapping_source_id:binding.mapping_source_id, facts,
 };
}

// Display links and GLB metadata never enter the compatible API request.
export function apiContext(context) {
 if (!context.pane) return context;
 const {status, scene, scene_version, schema_version, pane, evidence_snapshot_id, facts} = context;
 return {status, scene, scene_version, schema_version, pane, evidence_snapshot_id, facts};
}

export function readFactSelection(answer, context) {
 const payload = JSON.parse(answer);
 assert(plain(payload) && payload.pane_id === context.pane.pane_id && Array.isArray(payload.fact_ids)
  && Object.keys(payload).every(key => ['pane_id','fact_ids'].includes(key)), '接口回复与当前窗片或证据契约不匹配。');
 const byId = new Map(context.facts.map(row => [row.id,row]));
 assert(payload.fact_ids.length > 0 && payload.fact_ids.every(id => byId.has(id)), '接口引用了未知的窗片证据。');
 return [...new Set(payload.fact_ids)].map(id => byId.get(id));
}

const paneQuestion = /窗片|窗格|玻璃|鸟撞|撞窗|碰撞|概率|校准|减撞|防撞|本地效果|改造效果|\b(?:pane|panes|window|windows|glazing|glass|collision|collisions|risk|risks|probability|probabilities|retrofit|retrofits|effectiveness)\b/i;
export function pendingPaneAnswer(text) {
 return paneQuestion.test(text) ? '当前选区缺少现场注册的窗片证据。可先在模型数据中定位窗片、核对现场照片和监测资料；碰撞概率和本地改造效果仍待验证。' : null;
}

export function factText(fact) {
 const value = fact.value === null ? '' : fact.id === 'optical_mechanism' ? optics[fact.value]
  : fact.unit === 'fraction' ? String(fact.value) + '（比例）'
  : String(fact.value) + ({'%':'%',count:' 次'}[fact.unit] || '');
 const fields = [names[factType(fact.id)], fact.view_id, stateText[fact.status], value, fact.observed_at, fact.evidence_tier];
 return fields.filter(Boolean).join(' · ');
}

let currentSelection = {scene:'campus', status:'empty'}, currentBundle = null;
let snapshot = buildContext(currentSelection);
const listeners = new Set();
export function getWorkspaceContext() { return snapshot; }
export function subscribeWorkspace(listener) {
 listeners.add(listener);
 return () => listeners.delete(listener);
}
export function refreshWorkspaceContext() {
 const next = buildContext(currentSelection,currentBundle);
 if (JSON.stringify(next) !== JSON.stringify(snapshot)) {
  snapshot = next;
  for (const listener of listeners) listener();
 }
 return snapshot;
}
export function setWorkspaceSelection(selection) {
 currentSelection = selection;
 refreshWorkspaceContext();
}
export function setPaneEvidence(bundle) {
 currentBundle = bundle;
 refreshWorkspaceContext();
}
export function revealWorkspaceEvidence(factId) {
 document.getElementById('show-data').click();
 const row = document.getElementById('pane-fact-' + factId);
 if (row) {
  row.focus();
  row.scrollIntoView({block:'center'});
 }
}
