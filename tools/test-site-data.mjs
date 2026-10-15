import assert from 'node:assert/strict';
import {makeSnapshot,sampleInfo} from './build-site-data.mjs';
const REPO='MythologIQ-Labs-LLC/agent-memory', SHA='a'.repeat(40);
const lane={lane_id:'parity-v1',status:'accepted',accepted_on:'2026-10-01',input_sha256:'b'.repeat(64),harness_revision:SHA,lane_file:'lanes/parity-v1.json',llm_calls:false,accepted_rows:[
{provider:'agent_memory',role:'control',system_revision:SHA,evidence:'runs/am.json',native:{'recall_all@5':0.6,scored_questions:20}},
{provider:'mem0_explicit',role:'comparator',system_revision:SHA,evidence:'runs/mem0.json',native:{'recall_all@5':0.7,scored_questions:20}},
{provider:'bm25',role:'baseline',system_revision:SHA,evidence:'runs/bm25.json',native:{'recall_all@5':0.9,scored_questions:20}}
]};
const dashboard={schema_version:2,authority_effect:'none',as_of:'2026-10-01',competitive_evidence:{frozen_lanes:[lane]},published_reference:[{system:'external',signals:{'accuracy':0.9},source:'https://example.com'}]};
const registry={schema_version:1,systems:[{id:'agent-memory',name:'Agent Memory',state:'measured',url:'https://example.com/am',observed_ids:['agent_memory']},{id:'mem0',name:'Mem0',state:'measured',url:'https://example.com/mem0',observed_ids:['mem0_explicit']},{id:'tencentdb-agent-memory',name:'TencentDB Agent Memory',state:'not_run',url:'https://example.com/tencent',observed_ids:[]}]};
const run=(d=dashboard,c=registry)=>makeSnapshot(d,c,{repo:REPO,head:SHA,blob:SHA});
const out=run(), m=out.profiles[0].metrics[0];
assert.equal(m.metric,'recall_all@5');assert.equal(m.best_score,0.7);assert.equal(m.gap_to_best,0.1);assert.equal(m.agent_memory_score,0.6);
assert.equal(m.rows.find(r=>r.role==='baseline').score,0.9);
assert.equal(out.competitors[2].state,'not_run');
assert.equal(out.published_reference[0].eligible_for_numeric_delta,false);
assert.ok(m.rows.every(r=>r.run_url.includes('/blob/'+SHA+'/')));
assert.throws(()=>run(dashboard,{...registry,systems:registry.systems.map(s=>s.id==='tencentdb-agent-memory'?{...s,state:'measured'}:s)}),/lacks accepted/);
assert.throws(()=>run(dashboard,{...registry,systems:registry.systems.map(s=>s.id==='mem0'?{...s,state:'not_run'}:s)}),/has accepted/);
assert.throws(()=>run(dashboard,{...registry,systems:[...registry.systems,registry.systems[0]]}),/duplicate/);
assert.throws(()=>run({...dashboard,competitive_evidence:{frozen_lanes:[{...lane,accepted_rows:lane.accepted_rows.map((r,i)=>i===0?{...r,evidence:'../secret.json'}:r)]}}),/Untrusted evidence path/);
assert.throws(()=>run({...dashboard,competitive_evidence:{frozen_lanes:[{...lane,accepted_rows:lane.accepted_rows.map((r,i)=>i===0?{...r,native:{'recall_all@5':1.6}}:r)]}}),/Invalid fraction/);
console.log('PASS: deterministic leaderboard projection, status guards, source pinning, and evidence validation');

assert.equal(sampleInfo({native:{total_passes:'15/77'}},'amb-precisionmembench-retrieval-v1').value,77);
assert.equal(sampleInfo({native:{total_passes:'6/0'}},'amb-precisionmembench-retrieval-v1').value,null);
assert.equal(sampleInfo({native:{total_passes:'78/77'}},'amb-precisionmembench-retrieval-v1').value,null);
assert.equal(sampleInfo({native:{total_passes:'15/77'}},'unrelated-benchmark-v1').value,null);
assert.equal(sampleInfo({native:{scored_questions:23}},'longmemeval-parity-v1').value,23);
