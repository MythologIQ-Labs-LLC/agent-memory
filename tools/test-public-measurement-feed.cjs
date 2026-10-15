'use strict';
/* Versioned measurement feed contract. No CI, network or benchmark execution. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const f=require('../assets/public-measurement-feed.js');
// The live feed belongs to a separate data-only branch, not gh-pages.
const feedPath=process.argv[2]||process.env.AGENT_MEMORY_PUBLIC_FEED_PATH;
if(!feedPath)throw Error('Pass locally materialized benchmark-public-feed/v1.json as the first argument');
const source=JSON.parse(fs.readFileSync(path.resolve(feedPath),'utf8'));
assert.equal(f.validate(source).profiles.length,7);
const copy=x=>structuredClone(x);
const bad=(fn)=>{const x=copy(source);fn(x);assert.throws(()=>f.validate(x),Error)};
bad(x=>{x.authority_effect='accepted'});
bad(x=>{x.profiles[0].evidence_status='accepted'});
bad(x=>{x.profiles[0].rows[0].status='accepted'});
bad(x=>{x.profiles[0].rows[0].artifact='../../secret.json'});
bad(x=>{x.profiles[0].rows[0].artifact_sha256='garbage'});
bad(x=>{x.profiles[0].rows[0].source_commit='not-a-sha'});
bad(x=>{x.profiles[0].rows[0].expected_score=1.2});
bad(x=>{x.profiles[0].rows[1].system=x.profiles[0].rows[0].system});
bad(x=>{x.profiles[0].cohort.scored_count=42});
bad(x=>{x.profiles[0].rows[0].extract.path=['__proto__']});
bad(x=>{x.profiles[3].rows[0].engine_revision='nonsense'});
bad(x=>{x.profiles[3].rows[0].extract.type='unknown'});
const independent=source.profiles.find(p=>p.id==='candidate:819:independent-holdout:176:strict');
assert.ok(independent&&independent.evidence_status==='candidate');
const iRows=Object.fromEntries(independent.rows.map(r=>[r.system,r]));
const agg=pass=>JSON.stringify({
 cohort_id:'am-819-holdout-v1',
 cases_sha256:independent.cohort.input_sha256,
 harness_sha256:independent.evaluator_revision,
 summary:{overall:{queries:176,strict_pass:pass,eval_failures:0,
  isolation_leaks:0,forgotten_leaks:0,stale_returned:0}}
});
assert.equal(f.evaluate(independent,iRows.agent_memory_baseline,agg(37)),37/176);
assert.equal(f.evaluate(independent,iRows.agent_memory_c1,agg(116)),116/176);
assert.equal(f.evaluate(independent,iRows.agent_memory_c2,agg(116)),116/176);
assert.throws(()=>f.evaluate(independent,iRows.agent_memory_c2,agg(177)),/count numerator/);
const invalidIdentity=JSON.parse(agg(116));invalidIdentity.cases_sha256='0'.repeat(64);
assert.throws(()=>f.evaluate(independent,iRows.agent_memory_c2,
 JSON.stringify(invalidIdentity)),/identity/);
const leaked=JSON.parse(agg(116));leaked.summary.overall.forgotten_leaks=1;
assert.throws(()=>f.evaluate(independent,iRows.agent_memory_c2,
 JSON.stringify(leaked)),/safety/);
bad(x=>{x.profiles[6].rows[0].extract.numerator_path=['__proto__']});
const csv='query_id,correct,why\nq1,True,"example, with comma"\nq2,False,skip\n';
assert.deepEqual(f.csvVerdicts(csv),{sample_count:2,scored_count:2,correct:1,score:0.5});
assert.throws(()=>f.csvVerdicts(csv.replace('q2','q1')),/duplicate/);
assert.throws(()=>f.csvVerdicts('query_id,correct\nq1,Maybe'),/verdict/);
const c2amb=source.profiles.find(p=>p.id==='candidate:819:amb:strict:baseline-vs-c2');
const ambdoc={before:{strict_success:0.1948},after:{strict_success:0.5065}};
assert.equal(f.evaluate(c2amb,c2amb.rows[0],JSON.stringify(ambdoc)),0.5065);
assert.equal(f.evaluate(c2amb,c2amb.rows[1],JSON.stringify(ambdoc)),0.1948);
const c2session=source.profiles.find(p=>p.id==='candidate:819:longmemeval-s:full500:session:c2');
const x={runs:{candidate_default:{agent_memory_revision:'eaf60e4dd001c02ce00bb36f15f800996bf77da3',
 metrics:{'recall_all@10':0.754177}},baseline:{agent_memory_revision:'1df28f84c236f5369b004465252610bd88ae07c9',
 metrics:{'recall_all@10':0.892601}}}};
assert.equal(f.evaluate(c2session,c2session.rows[0],JSON.stringify(x)),0.754177);
assert.equal(f.evaluate(c2session,c2session.rows[1],JSON.stringify(x)),0.892601);
x.runs.candidate_default.agent_memory_revision='f'.repeat(40);
assert.throws(()=>f.evaluate(c2session,c2session.rows[0],JSON.stringify(x)),/revision identity/);
const mismatch=copy(source.profiles[2]);mismatch.cohort.sample_count=78;
assert.throws(()=>f.evaluate(mismatch,mismatch.rows[0],csv),/population mismatch/);
const from=copy(source);
from.profiles[0].rows[0].expected_score=0.999999;
assert.equal(f.validate(from),from); // Native digest and metric comparison occurs in processFeed.
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
assert.match(html,/assets\/public-measurement-feed.js/);
assert.match(html,/id="measuredRows"/);
assert.match(html,/All measured results \(default\)/);
const script=fs.readFileSync(path.join(__dirname,'../assets/measured-leaderboard.js'),'utf8');
assert.match(script,/agent-memory:public-feed/);
assert.match(script,/publicFeedProfiles/);
console.log('PASS: seven cohorts, strict scoring/source boundaries, C2 A-B scores and runtime revision identity, stable leaderboard hook.');
