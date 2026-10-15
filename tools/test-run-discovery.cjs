'use strict';
/* Pure offline contract tests for candidate discovery. No remote GitHub API calls. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const d=require('../assets/run-discovery.js');
const config=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/live-sources.json'),'utf8'));
assert.equal(d.validateSources(config).length,2);
const clone=x=>structuredClone(x);
const from=clone(config);
from.authority_effect='accepted';assert.throws(()=>d.validateSources(from),/Invalid/);
from.authority_effect='none';from.sources[0].prefix='private/';assert.throws(()=>d.validateSources(from),/Invalid/);
from.sources[0].prefix='reports/benchmarks/runs/';
from.sources[1].branch=from.sources[0].branch;assert.throws(()=>d.validateSources(from),/Invalid/);
const SHA='a'.repeat(64);
const BASE='reports/benchmarks/runs/640-hindsight/subset50/';
const pathManifest=BASE+'session.hindsight_chunks_onnx.manifest.json';
const m={
 schema_version:'1.0.0',authority_effect:'none',run_id:'hs:subset50:session:hindsight_chunks_onnx',
 benchmark:{id:'longmemeval-s-retrieval',task_profile:'longmemeval-s-retrieval-parity-v1:session',
 input_sha256:SHA,sample_count:50,excluded_count:7,
 selection_id:'size=50|ids_sha256='+'b'.repeat(64)},
 system:{id:'hindsight',adapter_revision:'git-blob:'+'c'.repeat(40)},
 normalized_run:{uri:BASE+'hindsight-50.json',sha256:'d'.repeat(64)},
 execution:{exit_code:0},review:{status:'candidate',comparison_eligibility:'not_assessed'}
};
const identity=d.validateManifest(m,pathManifest);
assert.deepEqual(identity,{plane:'session',backend:'hindsight_chunks_onnx'});
const mutate=(fn,message)=>{const x=clone(m);fn(x);assert.throws(()=>d.validateManifest(x,pathManifest),Error,message)};
mutate(x=>x.authority_effect='accepted','authority boundary');
mutate(x=>x.review.status='accepted','not official');
mutate(x=>x.execution.exit_code=1,'must run');
mutate(x=>x.normalized_run.uri='../../secrets','path traversal');
mutate(x=>x.benchmark.excluded_count=51,'invalid population');
mutate(x=>x.run_id='wrong:turn:backend','backend binding');
const report={input:{sha256:SHA,question_count:50,selection:{question_ids_sha256:'b'.repeat(64)}},
 planes:{session:{backends:{hindsight_chunks_onnx:{
 aggregate:{evaluated_question_count:43,excluded_abstention_count:3,
 excluded_no_user_target_count:4,headline:{'recall_all@5':0.930233}},
 failures:{runtime_failure_count:0,ingestion_failure_count:0,out_of_corpus_returned_count:0}
 }}}}};
assert.deepEqual(d.extractMetric(report,m,identity),{metric:'recall_all@5',score:0.930233,scored:43,excluded:7});
let changed=clone(report);changed.planes.session.backends.hindsight_chunks_onnx.failures.runtime_failure_count=1;
assert.throws(()=>d.extractMetric(changed,m,identity),/Missing or failed/);
changed=clone(report);changed.input.selection.question_ids_sha256='0'.repeat(64);
assert.throws(()=>d.extractMetric(changed,m,identity),/selection mismatch/);
changed=clone(report);changed.planes.session.backends.hindsight_chunks_onnx.aggregate.evaluated_question_count=42;
assert.throws(()=>d.extractMetric(changed,m,identity),/denominator mismatch/);
changed=clone(report);changed.planes.session.backends.hindsight_chunks_onnx.aggregate.headline['recall_all@5']=2;
assert.throws(()=>d.extractMetric(changed,m,identity),/out of range/);
const unknown=clone(m);unknown.benchmark.id='some-new-benchmark';
assert.equal(d.extractMetric(report,unknown,identity),null);
const partialPath='reports/benchmarks/runs/811-cognee/subset50/session.cognee_gliner_local.summary.json';
const partial={question_count_completed:15,question_count_preregistered:50,
 aggregate:{evaluated_question_count:14},missing_question_ids:Array.from({length:35},(_,i)=>String(i)),
 failures:{runtime_failure_count:0,ingestion_failure_count:0,out_of_corpus_returned_count:0}};
assert.deepEqual(d.validateSummary(partial,partialPath),
{plane:'session',backend:'cognee_gliner_local',completed:15,scored:14,planned:50});
let p=clone(partial);p.missing_question_ids=[];
assert.throws(()=>d.validateSummary(p,partialPath),/Unqualified/);
p=clone(partial);p.failures.ingestion_failure_count=1;
assert.throws(()=>d.validateSummary(p,partialPath),/Unqualified/);
const t={truncated:false,tree:[
{type:'blob',path:pathManifest,size:6180},
{type:'blob',path:partialPath,size:6179},
{type:'blob',path:'other/private.json',size:100},
{type:'blob',path:'reports/benchmarks/runs/bad/../../secret.manifest.json',size:30}]};
let discover=d.listFiles(t,config.sources[0]);
assert.deepEqual(discover.manifest,[pathManifest]);
assert.deepEqual(discover.partial,[partialPath]);
// Full-500 progress summaries can exceed 20 KB due to question ID lists.
const bigPath='reports/benchmarks/runs/fixture500/session.large.summary.json';
assert.deepEqual(d.listFiles({truncated:false,tree:[
 {type:'blob',path:bigPath,size:72000}]},config.sources[0]).partial,[bigPath]);
assert.deepEqual(d.listFiles({truncated:false,tree:[
 {type:'blob',path:bigPath,size:262145}]},config.sources[0]).partial,[]);
t.truncated=true;assert.throws(()=>d.listFiles(t,config.sources[0]),/truncated/);
const row=d.createRow(m,pathManifest,'e'.repeat(40),identity,d.extractMetric(report,m,identity));
assert.equal(row.score,0.930233);
assert.equal(row.cohort,'50 input · preregistered subset');
const progress=d.createPartial(partialPath,'e'.repeat(40),d.validateSummary(partial,partialPath));
assert.equal(progress.score,null);
assert.match(progress.coverage,/15\/50 completed/);
assert.equal(progress.cohort,'50 input · preregistered evaluation');
// Progress denominators must be sourced from preregistration, not hardcoded 50.
const full500=clone(partial);
full500.question_count_preregistered=500;
full500.question_count_completed=12;
full500.aggregate.evaluated_question_count=10;
full500.missing_question_ids=Array.from({length:488},(_,i)=>String(i));
const fullProgress=d.validateSummary(full500,partialPath);
assert.equal(fullProgress.planned,500);
assert.equal(fullProgress.completed,12);
assert.match(d.createPartial(partialPath,'e'.repeat(40),fullProgress).coverage,/12\/500 completed/);
const badDuplicate=clone(full500);
badDuplicate.missing_question_ids[1]=badDuplicate.missing_question_ids[0];
assert.throws(()=>d.validateSummary(badDuplicate,partialPath),/Unqualified/);
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
assert.match(html,/id="discoveredRunRows"/);
assert.match(html,/run-discovery.js/);
console.log('PASS: source-branch allowlist, manifest integrity, native denominator, no score for unknown/partial/failed, safe paths, source discovery');
