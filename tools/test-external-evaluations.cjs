/* Offline regression guard for the external evaluation directory. No network calls. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {validate,render} = require('../assets/external-evaluations.js');

const fixture = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'data', 'external-evaluations.json'), 'utf8'
));
const clone = () => structuredClone(fixture);
const rejects = (mutate, message) => {
  const d = clone();
  mutate(d);
  assert.throws(() => validate(d), Error, message);
};

assert.equal(validate(fixture), fixture);
assert.equal(fixture.programs.length, 3);
assert.deepEqual(new Set(fixture.programs.map(x => x.id)),
  new Set(['aml','amb','memoryarena']));
assert.ok(fixture.programs.every(x => x.official_result === null));
assert.ok(fixture.programs.every(x => x.status !== 'official_published'));
assert.ok(fixture.programs.every(x => x.program_url.startsWith('https://')));
assert.equal(fixture.programs.find(x => x.id === 'amb').status, 'adapter_present');
assert.equal(fixture.programs.find(x => x.id === 'aml').submission_deadline, '2026-10-31');
assert.equal(fixture.programs.find(x => x.id === 'aml').submission_timezone, 'UTC+08:00');

rejects(d => {d.authority_effect = 'write'}, 'directory cannot mutate authority');
rejects(d => {d.programs[0].id = d.programs[1].id}, 'duplicate program');
rejects(d => {d.programs[0].status = 'official_published'}, 'false official status');
rejects(d => {d.programs[0].program_url = 'javascript:alert(1)'}, 'unsafe URL');
rejects(d => {d.programs[0].method_url = 'https://user:pass@example.com/'}, 'URL credentials');
rejects(d => {d.programs[0].summary = ''}, 'missing meaningful status');
rejects(d => {d.programs[0].submission_timezone = 'UTC'}, 'deadline timezone');
rejects(d => {d.programs[0].official_result = {score:99}}, 'unreviewed score');
rejects(d => {d.programs[0].id = 'not-expected'}, 'unexpected program registry');
rejects(d => {d.programs[0].category = '<script>bad</script>';d.programs[0].official_result={score:45}}, 'external score lacks proof');
rejects(d => {d.programs.pop()}, 'missing external project');

const official = clone();
official.programs[0].status = 'official_published';
official.programs[0].official_result = {
  reviewed:true, metric:'Overall', dataset:'Track 1',
  evaluator_revision:'AML-2026-11',
  agent_memory_revision:'a'.repeat(40),
  score:50, evaluation_date:'2026-11-15',
  public_result_url:'https://agentmemoryleaderboard.ai/'
};
validate(official); // Future verified data has an explicit typed schema.
rejects(d => {
  d.programs[0].status='official_published';
  d.programs[0].official_result = {...official.programs[0].official_result,reviewed:false};
}, 'unreviewed future result');
rejects(d => {
  d.programs[0].status='official_published';
  d.programs[0].official_result = {...official.programs[0].official_result,public_result_url:'data:text/html,evil'};
}, 'unsafe score proof URL');

const nodes = {externalProgramGrid:{innerHTML:''},externalAsOf:{textContent:''}};
const doc = {getElementById:id => nodes[id] || null};
render(doc, fixture);
const out = nodes.externalProgramGrid.innerHTML;
assert.match(out, /Agent Memory Leaderboard/);
assert.match(out, /Agent Memory Benchmark/);
assert.match(out, /MemoryArena/);
assert.match(out, /No independently verified official Agent Memory score/);
assert.doesNotMatch(out, /Official Overall/);
assert.match(out, /rel="noopener noreferrer"/);
assert.match(nodes.externalAsOf.textContent, /manually maintained/);
const hostile = clone();
hostile.programs[0].category = '<img src=x onerror=alert(1)>';
render(doc, hostile);
assert.doesNotMatch(nodes.externalProgramGrid.innerHTML, /<img/);
assert.match(nodes.externalProgramGrid.innerHTML, /&lt;img/);
console.log('PASS: 3 verified program links; 13 negative/source integrity assertions; DOM output is safely escaped.');
