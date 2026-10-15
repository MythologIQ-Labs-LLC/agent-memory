'use strict';
/* No network, no GH Actions, no benchmark execution. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const api=require('../assets/live-evidence.js');
const ID='d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442';
const SELECT='5266568e2e883b64e92e0da632d5e24c3fd61d8a447de7e629ebf93ef26a7339';
const makeReport=(n=50)=>({
 input:{sha256:ID,question_count:n,selection:{question_ids_sha256:SELECT}},
 planes:Object.fromEntries(['session','turn'].map(plane=>[plane,{backends:{
  agent_memory:{aggregate:{evaluated_question_count:43,excluded_abstention_count:3,
    excluded_no_user_target_count:4,headline:{'recall_all@5':0.837209,'recall_all@10':0.72093}},
    failures:{runtime_failure_count:0,ingestion_failure_count:0,out_of_corpus_returned_count:0}}
 }}]))
});
const report=makeReport();
assert.equal(api.reportParity(report,50),report);
assert.equal(api.scoreFor(report,'session','agent_memory','recall_all@5'),0.837209);
assert.equal(api.scoreFor(report,'turn','agent_memory','recall_all@10'),0.72093);
assert.equal(api.scoreFor(report,'session','missing','recall_all@5'),null);
assert.equal(api.scoreFor(report,'turn','agent_memory','unknown-metric'),null);
const clone=x=>JSON.parse(JSON.stringify(x));
let broken=clone(report);broken.input.sha256='a'.repeat(64);
assert.throws(()=>api.reportParity(broken,50),/selection identity/);
broken=clone(report);broken.input.selection.question_ids_sha256='b'.repeat(64);
assert.throws(()=>api.reportParity(broken,50),/selection identity/);
broken=clone(report);broken.planes.session.backends.agent_memory.failures.runtime_failure_count=1;
assert.equal(api.scoreFor(broken,'session','agent_memory','recall_all@5'),null);
broken=clone(report);broken.planes.session.backends.agent_memory.aggregate.evaluated_question_count=42;
assert.equal(api.scoreFor(broken,'session','agent_memory','recall_all@5'),null);
broken=clone(report);broken.planes.session.backends.agent_memory.aggregate.headline['recall_all@5']=2;
assert.equal(api.scoreFor(broken,'session','agent_memory','recall_all@5'),null);
const partial={question_count_completed:15,question_count_preregistered:50,
 aggregate:{evaluated_question_count:14},missing_question_ids:Array.from({length:35},(_,i)=>String(i)),
 failures:{runtime_failure_count:0,ingestion_failure_count:0,out_of_corpus_returned_count:0}};
assert.equal(api.checkPartial(partial,'Cognee').completed,15);
assert.equal(api.checkPartial(null,'Cognee'),null);
broken=clone(partial);broken.question_count_completed=50;
assert.throws(()=>api.checkPartial(broken,'Cognee'),/Incomplete or failed/);
broken=clone(partial);broken.failures.ingestion_failure_count=1;
assert.throws(()=>api.checkPartial(broken,'Cognee'),/Incomplete or failed/);
const csv='query_id,category,pass_type,correct,judge_reason\n'+
 'a,Scope,active,True,pass\n'+
 'b,Scope,active,False,"unexpected belief in relevantBeliefs: x, y"\n'+
 'c,Scope,active,False,missing expected belief\n';
assert.deepEqual(api.parseCSV(csv),{total:3,correct:1,failed:2,excessFailures:1});
assert.throws(()=>api.parseCSV(csv.replace('c,Scope','a,Scope')),/repeated/);
assert.throws(()=>api.parseCSV('query_id,correct\na,True'),/schema mismatch/);
assert.throws(()=>api.parseCSV('query_id,category,pass_type,correct,judge_reason\na,b,c,maybe,d'),/verdict missing/);
assert.throws(()=>api.makeUrl('a'.repeat(40),'../../secret'),/Unsafe/);
assert.throws(()=>api.makeUrl('a'.repeat(32),'reports/ok.json'),/Unsafe/);
assert.match(api.makeUrl('a'.repeat(40),'reports/runs/summary.json'),/raw.githubusercontent.com/);
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
assert.match(html,/id="live-runs"/);
assert.match(html,/id="liveCompetitorRows"/);
assert.match(html,/id="liveExternalResults"/);
assert.match(html,/assets\/live-evidence.js/);
assert.match(html,/not official placements or accepted gauntlet scores/);
console.log('PASS: candidate source/parity, no score for partial/failed runs, CSV quote/parser, provenance paths, site integration');
