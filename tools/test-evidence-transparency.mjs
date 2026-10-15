#!/usr/bin/env node
/* Offline, dependency-free checks for the published evidence transparency surface.
   No GitHub Actions, model inference, benchmark execution or browser network. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = fs.readFileSync(path.join(site,'assets/evidence-transparency.js'),'utf8');
const data = JSON.parse(fs.readFileSync(path.join(site,'data/snapshot.json'),'utf8'));
const sandbox = {};
vm.runInNewContext(source,sandbox,{timeout:1000});
const {audit,csv} = sandbox.AgentMemoryPeerEvidence;
const snapshot = audit(data);
const clone = () => JSON.parse(JSON.stringify(data));
const negative = (edit, message) => {
  const changed = clone();
  edit(changed);
  assert.throws(()=>audit(changed),message);
};

assert.equal(snapshot.summary.measuredExternalProducts,1);
assert.equal(snapshot.summary.targetRemaining,5);
assert.equal(snapshot.summary.acceptedPlanes,6);
assert.equal(snapshot.summary.metricContexts,28);
assert.equal(snapshot.summary.benchmarkFamilies,2);
assert.equal(snapshot.summary.registeredUnmeasured,7);
assert.equal(snapshot.summary.distinctEvidenceLinks,18);
assert.equal(snapshot.summary.linksMissingSampleCounts,0);
assert.equal(snapshot.summary.observedComparatorLinks,6);
assert.equal(snapshot.metricRows.filter(r=>r.family==='AMB PrecisionMemBench' && r.sample_count!==77).length,0);
assert.equal(snapshot.profiles.every(p => p.columns.find(x=>x.id==='mem0').accepted),true);
assert.equal(snapshot.profiles.some(p => p.columns.find(x=>x.id==='tencentdb-agent-memory').accepted),false);
assert.equal(snapshot.measuredIds.includes('mem0-explicit'),true);
assert.equal(snapshot.measuredIds.includes('bm25'),false);
assert.equal(snapshot.measuredIds.includes('agent-memory'),false);
const output = csv(snapshot);
assert.ok(output.includes(data.source.head));
assert.ok(!output.includes('tencentdb'));
assert.equal(output.trim().split(/\r?\n/).length,85);
negative(x=>{x.profiles[0].metrics[0].rows[0].run_url='https://example.com/not-pinned.json'},/not pinned/);
negative(x=>{x.competitors.find(s=>s.id==='mem0').state='not_run'},/not registered as measured/);
negative(x=>{x.competitors.find(s=>s.id==='tencentdb-agent-memory').state='measured'},/lack accepted score/);
negative(x=>{x.profiles[0].metrics[0].rows[0].role='not_run'},/Unknown metric role/);
negative(x=>{x.source.authority_effect='write'},/Untrusted/);
const injection={...snapshot,metricRows:[{
  profile:'=HYPERLINK("https://malicious.example")',family:'test',plane:'test',metric:'test',
  direction:'higher',system:'test',role:'comparator',score:0.5,
  sample_count:10,evidence:'https://example.com',source_head:data.source.head,snapshot_as_of:'2026-10-07'
}]};
assert.ok(csv(injection).includes('"\'=HYPERLINK'));
console.log('PASS: 22 competitive transparency assertions; exact historical snapshot, no invented scores');
