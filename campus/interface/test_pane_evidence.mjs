import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {apiContext,buildContext,factText,parsePaneEvidence,readFactSelection} from './pane_evidence.js';

const raw = JSON.parse(readFileSync(new URL('../../data/examples/synthetic_workspace_evidence.json', import.meta.url)));
const counts = new Map([['MAIN_CC',1],['LAKE_00',1]]);
const bundle = parsePaneEvidence(raw,'v89',counts);
const main = buildContext({scene:'campus',status:'model_object',object_name:'MAIN_CC'},bundle);
const neighbor = buildContext({scene:'campus',status:'model_object',object_name:'LAKE_00'},bundle);
const selection = (context,fact_ids) => JSON.stringify({pane_id:context.pane.pane_id,fact_ids});

test('evidence uses the same exact pane and source allowlist in detail and chat',()=>{
 assert.equal(main.pane.pane_id,'SYN-A-1');
 assert.equal(neighbor.pane.pane_id,'SYN-A-2');
 assert.equal(main.pane.facade_id,neighbor.pane.facade_id);
 const facts=readFactSelection(selection(main,['exterior_vlr','exterior_vlt']),main);
 assert.equal(facts[0].status,'conflict');
 assert.equal(facts[0].source_ids.length,2);
 assert.match(factText(facts[1]),/60%.*2026-01-09T09:00:00\+08:00/);
 assert.equal(facts[1],main.facts.find(fact=>fact.id==='exterior_vlt'));
 assert.equal(apiContext(main).facts,main.facts);
 assert.ok(!('mapping_source_id' in apiContext(main)));
});

test('reply IDs cannot introduce a neighbor, unsupported fact or arbitrary prose',()=>{
 assert.throws(()=>readFactSelection(selection(neighbor,['exterior_vlt']),main),/当前窗片/);
 assert.throws(()=>readFactSelection(selection(main,['collision_risk_numeric']),main),/未知/);
 assert.throws(()=>readFactSelection(JSON.stringify({
  pane_id:main.pane.pane_id,fact_ids:['exterior_vlt'],answer:'现场测量为 90%'
 }),main),/证据契约/);
 const unresolved=readFactSelection(selection(neighbor,['tree_cover_0_5_m','local_treatment_effect']),neighbor);
 assert.ok(unresolved.every(fact=>fact.value===null));
});

test('expired, empty and DSM context never retain stale pane measurements',()=>{
 const stale=buildContext({scene:'campus',status:'model_object',object_name:'MAIN_CC'},bundle,Date.parse('2100-01-01'));
 assert.equal(stale.facts.find(fact=>fact.id==='exterior_vlt').status,'stale');
 assert.equal(stale.facts.find(fact=>fact.id==='exterior_vlt').value,null);
 assert.ok(!buildContext({scene:'campus',status:'empty'},bundle).pane);
 assert.ok(!buildContext({scene:'dsm',status:'terrain_reference',object_name:'MAIN_CC'},bundle).pane);
});

test('invalid versions, mesh registrations, units, or local probabilities are rejected',()=>{
 assert.throws(()=>parsePaneEvidence(raw,'v88',counts),/版本/);
 assert.throws(()=>parsePaneEvidence({...raw,dataset_kind:'field'},'v89',counts),/相同的窗片/);
 const bad=structuredClone(raw);
 const vlr=bad.bindings[0].facts.find(fact=>fact.id==='exterior_vlr');
 vlr.unit='m';
 assert.throws(()=>parsePaneEvidence(bad,'v89',counts),/单位/);
 vlr.unit='%';
 const risk=bad.bindings[0].facts.find(fact=>fact.id==='glass_contact_risk');
 risk.value=0.5;
 assert.throws(()=>parsePaneEvidence(bad,'v89',counts),/空值/);
});
