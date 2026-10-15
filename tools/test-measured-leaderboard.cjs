'use strict';
/* Local-only, no benchmark runs and no external HTTP. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const modulePath=path.join(__dirname,'../assets/measured-leaderboard.js');
const board=require(modulePath);
const preview=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/candidate-leaderboard.json'),'utf8'));
const accepted=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/snapshot.json'),'utf8'));
const clone=x=>structuredClone(x);
assert.equal(board.validatedPreview(preview).length,3);
const session=preview.profiles.find(p=>p.id==='candidate:longmemeval-s:subset50:session');
const turn=preview.profiles.find(p=>p.id==='candidate:longmemeval-s:subset50:turn');
const amb=preview.profiles.find(p=>p.id==='candidate:amb:precisionmembench:77:strict');
const rank=rows=>([...rows].filter(x=>x.role!=='baseline').sort((a,b)=>b.score-a.score));
assert.deepEqual(rank(session.metrics[0].rows).map(x=>x.system),['hindsight','mem0','agent_memory']);
assert.deepEqual(rank(turn.metrics[0].rows).map(x=>x.system),['hindsight','agent_memory','mem0']);
assert.equal(amb.metrics[0].rows.find(x=>x.system==='agent_memory').score,15/77);
assert.equal(amb.metrics[0].rows.find(x=>x.system==='bm25').score,8/77);
assert.ok(!amb.metrics[0].rows.some(x=>x.system==='hindsight'));
assert.equal(session.scored_count,43);
assert.equal(accepted.source.authority_effect,'none');
const mutations=[
 x=>x.profiles[0].evidence_status='accepted',
 x=>x.profiles[0].dataset_sha256='b'.repeat(64),
 x=>x.profiles[0].metrics[0].rows[0].score=1.5,
 x=>x.profiles[0].metrics[0].rows[0].source_revision='f'.repeat(40),
 x=>x.profiles[0].metrics[0].rows[0].run_url='javascript:alert(1)',
 x=>x.profiles[0].metrics[0].rows[1].system=x.profiles[0].metrics[0].rows[0].system,
 x=>x.profiles[0].scored_count=50,
 x=>x.authority_effect='accepted',
];
for(const mut of mutations){const x=clone(preview);mut(x);
 assert.throws(()=>board.validatedPreview(x),Error);}
const fixture=[
 {kind:'manifest',benchmark:'longmemeval-s-retrieval',
 score:0.930233,systemId:'hindsight',name:'Hindsight',
 inputSha:session.dataset_sha256,selectionId:session.selection_id,
 evaluatorRevision:session.evaluator_revision,
 sampleCount:50,scoredCount:43,metric:'recall_all@5',plane:'session',
 review:'candidate',sha:session.source_commit,
 manifestPath:'reports/benchmarks/runs/640-hindsight/subset50/session.hindsight_chunks_onnx.manifest.json'},
 {kind:'manifest',benchmark:'longmemeval-s-retrieval',
 score:0.837209,systemId:'agent_memory',name:'Agent Memory',
 inputSha:session.dataset_sha256,selectionId:session.selection_id,
 evaluatorRevision:session.evaluator_revision,
 sampleCount:50,scoredCount:43,metric:'recall_all@5',plane:'session',
 review:'candidate',sha:session.source_commit,
 manifestPath:'reports/benchmarks/runs/controls/subset50/session.agent_memory.manifest.json'}
];
const candidates=board.discoveredProfiles(fixture);
assert.equal(candidates.length,1);
assert.equal(candidates[0].id,session.id);
assert.deepEqual(candidates[0].metrics[0].rows.map(r=>r.system),['hindsight','agent_memory']);
const shifted=clone(fixture);
shifted[1].selectionId='different selection';
assert.equal(board.discoveredProfiles(shifted).length,0);
const failure=clone(fixture);
failure[1].score=null;
assert.equal(board.discoveredProfiles(failure).length,0);
const unsafe=clone(fixture);
unsafe[1].manifestPath='reports/benchmarks/runs/../../secrets.manifest.json';
assert.equal(board.discoveredProfiles(unsafe).length,0);
const unknown=clone(fixture);
unknown[1].review='accepted';
assert.equal(board.discoveredProfiles(unknown).length,0);
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
assert.match(html,/id="measuredProfileSelect"/);
assert.match(html,/id="measuredRows"/);
assert.match(html,/All measured results \(default\)/);
assert.match(html,/assets\/measured-leaderboard.js/);
assert.match(html,/Accepted historical evidence/);
assert.match(html,/Source-pinned execution registry/);
console.log('PASS: honest candidate rankings, distinct populations, AMB strict case count, provenance guards, accepted-only filter, live-updated cohort identity, retained historical evidence');
