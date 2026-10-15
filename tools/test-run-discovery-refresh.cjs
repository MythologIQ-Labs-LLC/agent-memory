'use strict';
/* Offline browser orchestration test.
 * Run: node tools/test-run-discovery-refresh.cjs
 */
const assert=require('node:assert/strict');
const path=require('node:path');
const appPath=path.join(__dirname,'../assets/run-discovery.js');
const BRANCH='claude/817-jev-mem-execution-no-ci';
const SECOND='claude/wizardly-cray-bmkfrr';
const DATA='reports/benchmarks/runs/fixture500/session.fixture.summary.json';
const sha=n=>n.repeat(40);
const settings={
 schema_version:1,kind:'public-candidate-manifest-sources',
 authority_effect:'none',repository:'MythologIQ-Labs-LLC/agent-memory',
 read_only:true,sources:[
 {branch:BRANCH,prefix:'reports/benchmarks/runs/',max_manifest_files:48,max_partial_files:24},
 {branch:SECOND,prefix:'reports/benchmarks/runs/',max_manifest_files:48,max_partial_files:24}
 ]};
const testSummary=done=>({
 question_count_completed:done,question_count_preregistered:500,
 aggregate:{evaluated_question_count:done-2},
 missing_question_ids:Array.from({length:500-done},(_,i)=>'remaining-'+i),
 failures:{runtime_failure_count:0,ingestion_failure_count:0,
 out_of_corpus_returned_count:0}
});
let head='a',transient=false,fetches=0;
const nodes=Object.fromEntries(['discoveredRunRows','discoveredRunStatus','discoveredRunProblems']
 .map(id=>[id,{innerHTML:'',textContent:''}]));
const events=[];
globalThis.window={dispatchEvent:e=>events.push(e)};
globalThis.CustomEvent=class{constructor(type,options){this.type=type;this.detail=options.detail;}};
globalThis.document={getElementById:id=>nodes[id],readyState:'loading',addEventListener(){}};
globalThis.fetch=async url=>{
 const u=String(url);
 if(u==='./data/live-sources.json')return {ok:true,json:async()=>settings};
 if(u.includes('/git/ref/heads/')){
  const b=u.endsWith(BRANCH)?head:'d';
  return {ok:true,json:async()=>({object:{sha:sha(b)}})};
 }
 if(u.includes('/git/commits/')){
  const b=u.split('/').at(-1)[0];
  return {ok:true,json:async()=>({tree:{sha:sha(b==='a'?'f':b==='b'?'e':'c')}})};
 }
 if(u.includes('/git/trees/')){
  const tree=u.split('/git/trees/')[1].split('?')[0];
  return {ok:true,json:async()=>({truncated:false,tree:
    tree===sha('c')?[]:[{type:'blob',path:DATA,size:1500}]})};
 }
 if(u.endsWith('/'+DATA)){
  fetches++;
  if(transient)return {ok:false,status:503};
  return {ok:true,json:async()=>testSummary(head==='a'?12:16)};
 }
 throw Error('Unexpected request: '+u);
};
const app=require(appPath);
(async()=>{
 await app.refresh();
 assert.equal(app.getLastRows().length,1);
 assert.match(nodes.discoveredRunRows.innerHTML,/12\/500 completed/);
 head='b';transient=true;
 await app.refresh();
 assert.equal(app.getLastRows().length,1);
 assert.match(nodes.discoveredRunRows.innerHTML,/12\/500 completed/);
 assert.match(nodes.discoveredRunProblems.textContent,/503/);
 const attempts=fetches;
 transient=false;
 await app.refresh();
 assert.ok(fetches>attempts,'unchanged branch head must retry after transient artifact failure');
 assert.match(nodes.discoveredRunRows.innerHTML,/16\/500 completed/);
 assert.equal(app.getLastRows().length,1);
 assert.equal(events.at(-1).type,'agent-memory:candidate-runs');
 console.log('PASS: 500-question progress, stale-cache warning, unchanged-head retry, corrected evidence projection');
})().catch(e=>{console.error(e);process.exitCode=1;});
