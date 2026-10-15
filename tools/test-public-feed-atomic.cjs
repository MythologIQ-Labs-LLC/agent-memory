'use strict';
/* Offline integration test: updates are atomic; transient partial evidence retries.
 * Run: node tools/test-public-feed-atomic.cjs
 * Does not contact GitHub or execute benchmarks.
 */
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const path=require('node:path');
const ROOT='MythologIQ-Labs-LLC/agent-memory';
const SHA=c=>c.repeat(40);
const HASH=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const rows=new Map();
const item=(id,role,n,key)=>{
 const artifact='reports/benchmarks/fixture/'+id+'-'+key+'.json';
 const raw=JSON.stringify({score:n});
 rows.set(artifact,raw);
 return {system:id,label:id,role,status:'candidate',source_commit:SHA('c'),
 artifact,artifact_sha256:HASH(raw),extract:{type:'json_path',path:['score']},expected_score:n};
};
const first={id:'first',family:'fixture-memory',title:'Same frozen cohort',
 protocol:'local deterministic',evaluator_revision:'fixture-v1',metric:'score',
 method_note:'No official score',evidence_status:'candidate',
 cohort:{sample_count:10,scored_count:10,excluded_count:0,
 input_sha256:'d'.repeat(64),selection_id:'local-subset'},
 rows:[item('agent_memory','control',0.2,'1'),item('peer_alpha','comparator',0.3,'2')]};
const second={...first,id:'second',rows:[
 item('agent_memory','control',0.2,'3'),item('peer_beta','comparator',0.8,'4')]};
const feeds={
 a:{schema_version:1,kind:'agent-memory-measured-results-feed',authority_effect:'none',profiles:[first]},
 b:{schema_version:1,kind:'agent-memory-measured-results-feed',authority_effect:'none',profiles:[first,second]},
 c:{schema_version:1,kind:'agent-memory-measured-results-feed',authority_effect:'none',profiles:[second]}
};
let letter='a',transient=false,fetchAttempts=0;
const observed=[];
globalThis.window={crypto:crypto.webcrypto,dispatchEvent:event=>observed.push({type:event.type,detail:event.detail})};
globalThis.CustomEvent=class{constructor(type,props){this.type=type;this.detail=props.detail;}};
globalThis.fetch=async url=>{
 const u=String(url);
 if(u.endsWith('/git/ref/heads/benchmark-public-feed'))
  return {ok:true,json:async()=>({object:{sha:SHA(letter)}})};
 if(u.endsWith('/reports/benchmarks/public-feed/v1.json'))
  return {ok:true,json:async()=>feeds[letter]};
 const artifact=[...rows.keys()].find(p=>u.endsWith('/'+p));
 if(!artifact)throw Error('Unexpected fetch: '+u);
 fetchAttempts++;
 if(transient&&artifact.endsWith('peer_beta-4.json'))return {ok:false,status:503};
 const source=Buffer.from(rows.get(artifact),'utf8');
 const buffer=new Uint8Array(source).buffer;
 return {ok:true,arrayBuffer:async()=>buffer};
};
const api=require(path.join(__dirname,'../assets/public-measurement-feed.js'));
(async()=>{
 const simultaneousA=api.refresh();
 const simultaneousB=api.refresh();
 assert.equal(simultaneousA,simultaneousB,'overlapping refreshes must share one in-flight request');
 const a=await simultaneousA;
 assert.equal(a.length,1);
 assert.equal(api.getLastHead(),SHA('a'));
 letter='b';transient=true;
 await assert.rejects(()=>api.refresh(),/not applied/);
 assert.equal(api.getLastHead(),SHA('a'),'failed publication must not be pinned');
 assert.equal(api.getLastProfiles().length,1,'last full verification must remain visible');
 assert.equal(observed.at(-1).type,'agent-memory:public-feed-error');
 transient=false;
 const b=await api.refresh();
 assert.equal(b.length,2,'must retry identical head after failure');
 assert.equal(api.getLastHead(),SHA('b'));
 letter='c';
 const c=await api.refresh();
 assert.deepEqual(c.map(p=>p.id),['second'],'deliberately removed cohort stays removed');
 assert.equal(api.getLastHead(),SHA('c'));
 assert.equal(observed.at(-1).type,'agent-memory:public-feed');
 console.log('PASS: atomic feed publication, same-head retry, source withdrawal, explicit refresh error event; '+fetchAttempts+' source requests');
})().catch(error=>{console.error(error);process.exitCode=1;});
