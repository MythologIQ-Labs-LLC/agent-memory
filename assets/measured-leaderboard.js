/* Measured-outcomes leaderboard. Ranks each exact cohort, shows review state.
   Neither imports numbers into the accepted evidence snapshot nor asserts official placement. */
(function(root){
'use strict';
const R='MythologIQ-Labs-LLC/agent-memory';
const q=id=>document.getElementById(id);
const h=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const score=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0&&n<=1;
const pretty=n=>score(n)?(n*100).toFixed(2)+'%':'Not measured';
const statusName=s=>s==='accepted'?'Accepted':s==='reviewed_self_run_unofficial'?'Reviewed self-run · unofficial':'Candidate · awaiting qualification';
const scope=()=>q('measuredScope')?.value||'all';
const FROZEN='5266568e2e883b64e92e0da632d5e24c3fd61d8a447de7e629ebf93ef26a7339';
const INPUT='d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442';
let accepted=null,preview=null,observed=[],current=[],publicFeedProfiles=[],initialized=false;
const SAFE=/^https:\/\/github\.com\/MythologIQ-Labs-LLC\/agent-memory\/blob\/[0-9a-f]{40}\/[a-zA-Z0-9_.\/-]+$/;
function safeHref(url){return SAFE.test(url||'')&&!url.split('/').includes('..')?url:'#'}
function validatedPreview(d){
 if(!d||d.schema_version!==1||d.kind!=='candidate-measured-evidence-not-accepted'||
    d.authority_effect!=='none'||!Array.isArray(d.profiles)||d.profiles.length>20)throw Error('Invalid candidate registry');
 const ids=new Set();
 return d.profiles.map(p=>{
  if(typeof p.id!=='string'||ids.has(p.id)||p.evidence_status==='accepted'||
     !/^[0-9a-f]{40}$/.test(p.source_commit||'')||
     !Array.isArray(p.metrics)||p.metrics.length===0)throw Error('Invalid candidate profile');
  ids.add(p.id);
  for(const m of p.metrics) {
   if(!Array.isArray(m.rows)||m.rows.length===0||m.rows.some(r=>
     !score(r.score)||!Number.isInteger(r.sample_count)||r.sample_count<1||
     r.status!==p.evidence_status||r.source_revision!==p.source_commit||
     safeHref(r.run_url)==='#'))throw Error('Unproven candidate row');
   if(new Set(m.rows.map(r=>r.system)).size!==m.rows.length)throw Error('Duplicate contestant');
  }
  if(p.family==='longmemeval-s-retrieval'&&
    (p.dataset_sha256!==INPUT||!p.selection_id?.includes(FROZEN)||
    p.sample_count!==50||p.scored_count!==43||p.excluded_count!==7))
    throw Error('Frozen population mismatch');
  return p;
 });
}
function acceptedProfiles(){
 if(!accepted||accepted.schema_version!==1||
    accepted.source?.authority_effect!=='none'||!Array.isArray(accepted.profiles))
    return [];
 return accepted.profiles.map(p=>({
  id:'accepted:'+p.profile_id,title:p.lane_id+' · '+p.plane,
  family:p.lane_id,evidence_status:'accepted',sample_count:null,
  method_note:p.method_note,origin:'canonical accepted snapshot',
  metrics:p.metrics.map(m=>({metric:m.metric,rows:m.rows.map(r=>({
   system:r.system,label:r.system.replace(/[_-]/g,' '),
   role:r.role,score:r.score,sample_count:r.sample_count,
   status:'accepted',run_url:r.run_url
  }))}))
 }));
}
function previewProfiles(){
 return (preview||[]).map(p=>({...p,origin:'pinned candidate snapshot · 2026-10-15'}));
}
function discoveredProfiles(rows){
 const groups=new Map();
 for(const x of rows||[]){
  if(x.kind!=='manifest'||x.benchmark!=='longmemeval-s-retrieval'||!score(x.score)||
    !x.systemId||!x.inputSha||!x.selectionId||!x.evaluatorRevision||
    !Number.isInteger(x.sampleCount)||x.sampleCount<1||
    !Number.isInteger(x.scoredCount)||x.scoredCount<1||
    !['session','turn'].includes(x.plane)||x.metric!=='recall_all@'+(x.plane==='session'?5:10)||
    x.review==='accepted'||!/^([0-9a-f]{40})$/.test(x.sha||'')||
    (!/^reports\/benchmarks\/runs\/[a-zA-Z0-9_.\/-]+\.manifest\.json$/.test(x.manifestPath||'') || x.manifestPath.split('/').includes('..')))continue;
  const key=[x.sampleCount,x.plane,x.inputSha,x.selectionId,x.evaluatorRevision,x.metric].join('|');
  if(!groups.has(key))groups.set(key,[]);
  groups.get(key).push(x);
 }
 const profiles=[];
 for(const group of groups.values()){
  const first=group[0],seen=new Set(),items=[];
  for(const x of group){
   if(seen.has(x.systemId))continue;
   seen.add(x.systemId);
   const role=x.systemId==='agent_memory'?'control':
    ['lexical_overlap','bm25'].includes(x.systemId)?'baseline':'comparator';
   items.push({system:x.systemId,label:x.name,role,score:x.score,
     sample_count:x.scoredCount,status:'candidate',
     run_url:'https://github.com/'+R+'/blob/'+x.sha+'/'+x.manifestPath});
  }
  if(items.length<2||!items.some(x=>x.role==='control'))continue;
  const known=first.sampleCount===50&&first.inputSha===INPUT&&first.selectionId.includes(FROZEN);
  const id=known?'candidate:longmemeval-s:subset50:'+first.plane:
    'candidate:longmemeval-s:'+first.sampleCount+':'+first.plane+':'+
      first.selectionId.slice(-10);
  profiles.push({id,title:'LongMemEval-S · '+first.sampleCount+
    ' fixed questions · '+first.plane+' retrieval',
    evidence_status:'candidate',origin:'cryptographically verified source manifests',
    family:'longmemeval-s-retrieval',sample_count:first.sampleCount,
    method_note:'Source report bytes verified against exact manifest SHA-256. '+
     'Identical input/selection/evaluator/plane; scored population is displayed per contestant. '+
     'Retrieval only. Candidate, not an accepted or official QA score.',
    metrics:[{metric:first.metric,rows:items}]});
 }
 return profiles;
}
function profiles(){
 const acceptedRows=acceptedProfiles();
 if(scope()==='accepted')return acceptedRows;
 const candidates=new Map(previewProfiles().map(p=>[p.id,p]));
 for(const p of discoveredProfiles(observed)){
  const earlier=candidates.get(p.id);
  if(!earlier||p.metrics[0].rows.length>=earlier.metrics[0].rows.length)
   candidates.set(p.id,p);
 }
 // Source-verified public feed supersedes manually curated candidate fallbacks.
 // It never supplies accepted authority or changes the historical accepted snapshot.
 for(const p of publicFeedProfiles){
  if(p&&p.evidence_status!=='accepted'&&Array.isArray(p.metrics))
    candidates.set(p.id,p);
 }
 return [...candidates.values(),...acceptedRows];
}
function option(el,items,keep,defaultId){
 el.replaceChildren();
 for(const x of items){
  const op=document.createElement('option');op.value=x.id;op.textContent=x.text;el.append(op);
 }
 if(items.some(x=>x.id===keep))el.value=keep;
 else if(items.some(x=>x.id===defaultId))el.value=defaultId;
}
function updateProfiles(keep){
 current=profiles().filter(p=>p.metrics?.length);
 const el=q('measuredProfileSelect');
 option(el,current.map(p=>({id:p.id,text:(p.evidence_status==='accepted'?'ACCEPTED':'CANDIDATE')+
  ' · '+p.title})),keep,'candidate:longmemeval-s:subset50:session');
 updateMetrics();
}
function updateMetrics(selected){
 const p=current.find(x=>x.id===q('measuredProfileSelect').value);
 if(!p){q('measuredRows').textContent='No comparable benchmark evidence found.';return}
 option(q('measuredMetricSelect'),p.metrics.map(m=>({id:m.metric,text:m.metric.replaceAll('_',' ')})),
  selected,p.metrics[0].metric);
 render();
}
function render(){
 const p=current.find(x=>x.id===q('measuredProfileSelect').value);
 const m=p?.metrics.find(x=>x.metric===q('measuredMetricSelect').value);
 if(!m)return;
 const rows=m.rows.filter(r=>score(r.score));
 const revision=String(p.family||'').startsWith('runtime-revision-');
 const competitors=rows.filter(r=>revision||r.role!=='baseline');
 const order=[...competitors].sort((a,b)=>b.score-a.score);
 const am=order.find(r=>r.role==='control');
 const leader=revision?order.find(r=>r.system==='agent_memory_baseline'):order.find(r=>r.role==='comparator');
 const rank=am?1+order.filter(r=>r.score>am.score).length:null;
 const best=order.length?order[0].score:null;
 q('measuredMode').textContent=statusName(p.evidence_status);
 q('measuredMode').className='score-mode '+(p.evidence_status==='accepted'?'mode-accepted':'mode-candidate');
 q('measuredKpis').innerHTML=[
  [revision?'Leading revision':'Memory-system leader',order[0]?pretty(order[0].score):'Not measured'],
  [revision?'C2 candidate':'Agent Memory',am?pretty(am.score):'Not measured'],
  [revision?'C2 revision rank':'Agent Memory rank',rank?'#'+rank+' / '+order.length:'Not ranked'],
  [revision?'C2 vs original baseline':'Gap to strongest external memory system',leader&&am?
    ((am.score-leader.score)>=0?'+':'')+((am.score-leader.score)*100).toFixed(2)+' pp':revision?'Not measured':'No external measurement']
 ].map(([label,value])=>'<div class="measured-kpi"><span>'+h(label)+
  '</span><strong>'+h(value)+'</strong></div>').join('');
 q('measuredRows').innerHTML=[...rows].sort((a,b)=>b.score-a.score).map(r=>{
  const isBase=r.role==='baseline';
  const rankLabel=isBase&&!revision?'Baseline':'#'+(1+order.filter(x=>x.score>r.score).length);
  return '<tr'+(r.role==='control'?' class="measured-am"':'')+'>'+
   '<td class="measured-rank">'+h(rankLabel)+'</td>'+
   '<th scope="row">'+h(r.label||r.system)+'</th>'+
   '<td>'+h(r.role)+'</td>'+
   '<td class="measured-num">'+h(pretty(r.score))+'</td>'+
   '<td class="measured-num">'+h(r.sample_count??'Unknown')+'</td>'+
   '<td>'+h(isBase&&!revision?'Baseline':best!==null?((best-r.score)*100).toFixed(2)+' pp':'Unknown')+'</td>'+
   '<td><span class="measured-row-state">'+h(statusName(r.status||p.evidence_status))+'</span></td>'+
   '<td><a href="'+h(safeHref(r.run_url))+
    '" target="_blank" rel="noopener noreferrer">Evidence ↗</a></td></tr>';
 }).join('');
 q('measuredProvenance').textContent=p.origin+' · '+p.method_note+
  (revision?' Revision rank is ONLY relative to the two versions shown, not a product market ranking.':
  ' Rankings exclude baseline-only methods. Never combine different cohorts, evaluator protocols or native metrics.');
}
function setup(){
 if(initialized)return;initialized=true;
 q('measuredScope').addEventListener('change',()=>updateProfiles(null));
 q('measuredProfileSelect').addEventListener('change',()=>updateMetrics());
 q('measuredMetricSelect').addEventListener('change',render);
 root.addEventListener('agent-memory:public-feed',e=>{
  if(!Array.isArray(e.detail?.profiles))return;
  publicFeedProfiles=e.detail.profiles;
  const selected=q('measuredProfileSelect').value,metric=q('measuredMetricSelect').value;
  updateProfiles(selected);
  updateMetrics(metric);
 });
 root.addEventListener('agent-memory:candidate-runs',e=>{
  if(!Array.isArray(e.detail))return;
  observed=e.detail;
  const selected=q('measuredProfileSelect').value,metric=q('measuredMetricSelect').value;
  updateProfiles(selected);
  updateMetrics(metric);
 });
}
async function start(){
 setup();
 const result=await Promise.allSettled([
  fetch('./data/snapshot.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Accepted snapshot unavailable');return r.json()}),
  fetch('./data/candidate-leaderboard.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Candidate preview unavailable');return r.json()})
 ]);
 if(result[0].status==='fulfilled')accepted=result[0].value;
 if(result[1].status==='fulfilled') {
  try{preview=validatedPreview(result[1].value)}catch(e){
   q('measuredProvenance').textContent='Pinned candidate preview failed verification: '+e.message;
  }
 }
 if(root.AgentMemoryRunDiscovery?.getLastRows)observed=root.AgentMemoryRunDiscovery.getLastRows();
 if(root.AgentMemoryPublicFeed?.getLastProfiles)
  publicFeedProfiles=root.AgentMemoryPublicFeed.getLastProfiles();
 updateProfiles('candidate:longmemeval-s:subset50:session');
}
root.AgentMemoryMeasuredBoard={validatedPreview,discoveredProfiles,acceptedProfiles,profiles,render,start};
if(typeof module!=='undefined'&&module.exports)module.exports=root.AgentMemoryMeasuredBoard;
if(typeof document!=='undefined'){
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
 else start();
}
})(typeof window!=='undefined'?window:globalThis);
