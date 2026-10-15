'use strict';
/* Offline UI-state test, no DOM library or external network.
 * Run from gh-pages: node tools/test-leaderboard-feed-authority.cjs
 */
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const root=path.join(__dirname,'..');
const nodeIds=['measuredScope','measuredProfileSelect','measuredMetricSelect',
  'measuredRows','measuredMode','measuredKpis','measuredProvenance'];
const nodes=Object.fromEntries(nodeIds.map(id=>[id,{
 value:'',innerHTML:'',textContent:'',
 replaceChildren(){this.options=[];this.value='';},
 append(opt){(this.options??=[]).push(opt);if(!this.value)this.value=opt.value;},
 addEventListener(type,fn){(this.handlers??={})[type]=fn;}
}]));
nodes.measuredScope.value='all';
const eventHandlers={};
globalThis.window={
 addEventListener(type,fn){eventHandlers[type]=fn;},
 AgentMemoryRunDiscovery:{getLastRows:()=>[]},
 AgentMemoryPublicFeed:{getLastProfiles:()=>[]}
};
globalThis.document={
 getElementById:id=>nodes[id],
 createElement:()=>({value:'',textContent:''}),
 readyState:'loading',addEventListener(){}
};
const snapshot=JSON.parse(fs.readFileSync(path.join(root,'data/snapshot.json'),'utf8'));
const preview=JSON.parse(fs.readFileSync(path.join(root,'data/candidate-leaderboard.json'),'utf8'));
globalThis.fetch=async url=>({
 ok:true,json:async()=>String(url).includes('candidate-leaderboard')?preview:snapshot
});
const board=require(path.join(root,'assets/measured-leaderboard.js'));
const candidate={
 id:'candidate:amb:precisionmembench:77:strict',
 title:'AMB · same native run',family:'precisionmembench',
 evidence_status:'candidate',origin:'SHA-verified current feed',
 method_note:'77-case native scorer',
 metrics:[{metric:'strict_case_success',rows:[
 {system:'agent_memory',label:'Agent Memory',role:'control',score:15/77,
  sample_count:77,status:'candidate',run_url:'https://github.com/abc'},
 {system:'bm25',label:'BM25',role:'baseline',score:8/77,
  sample_count:77,status:'candidate',run_url:'https://github.com/abc'}
 ]}]
};
(async()=>{
 await board.start();
 assert.ok(board.profiles().some(p=>p.id==='candidate:longmemeval-s:subset50:session'));
 eventHandlers['agent-memory:public-feed']({detail:{profiles:[candidate]}});
 assert.ok(!board.profiles().some(p=>p.id==='candidate:longmemeval-s:subset50:session'),
  'once feed verifies, withdrawn fallback candidate must not be republished');
 assert.ok(board.profiles().some(p=>p.id.startsWith('accepted:')),
  'historically accepted profiles must remain present');
 nodes.measuredProfileSelect.value=candidate.id;
 nodes.measuredProfileSelect.handlers.change();
 assert.match(nodes.measuredKpis.innerHTML,/No measured peer/,
  'a lone product plus BM25 does not justify a first-place product rank');
 assert.match(nodes.measuredRows.innerHTML,/No peer/);
 eventHandlers['agent-memory:public-feed-error']({
  detail:{message:'new public feed revision not applied; one source invalid'}
 });
 assert.match(nodes.measuredProvenance.textContent,/DATA REFRESH WARNING/,
  'the failed update must be visible without redesigning the UI');
 eventHandlers['agent-memory:public-feed']({detail:{profiles:[candidate]}});
 assert.doesNotMatch(nodes.measuredProvenance.textContent,/DATA REFRESH WARNING/,
  'fresh validated feed should clear warning');
 nodes.measuredScope.value='accepted';
 nodes.measuredScope.handlers.change();
 assert.ok(board.profiles().every(p=>p.evidence_status==='accepted'),
  'accepted-only filter must never expose candidate rows');
 console.log('PASS: current data feed overrides fallback, source error visible, no false first-place claim, accepted archive retained.');
})().catch(error=>{console.error(error);process.exitCode=1;});
