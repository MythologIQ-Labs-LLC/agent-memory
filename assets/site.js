'use strict';
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url=value=>{try{const u=new URL(String(value));return u.protocol==='https:'?u.href:'#'}catch{return '#'}};
const pct=n=>typeof n==='number'?(100*n).toFixed(2)+'%':'Not measured';
const pp=n=>typeof n==='number'?(100*n).toFixed(2)+' pp':'—';
const friendly=s=>String(s).replaceAll('_',' ').replaceAll('-',' ').replace(/\b\w/g,c=>c.toUpperCase());
const stateLabel=s=>({not_run:'Not run',measured:'Measured',published_reference:'Published only'})[s]||s;
let catalog=null;
function setOptions(select,items){select.replaceChildren();for(const it of items){const opt=document.createElement('option');opt.value=it.value;opt.textContent=it.label;select.append(opt)}}
function renderMetric(){
 const profile=catalog.profiles.find(p=>p.profile_id===$('profileSelect').value);
 if(!profile){$('metricSummary').textContent='No comparable evidence in this profile.';$('leaderRows').replaceChildren();return}
 const metric=profile.metrics.find(m=>m.metric===$('metricSelect').value);
 if(!metric)return;
 const peers=metric.rows.filter(r=>r.role==='comparator'&&typeof r.score==='number').sort((a,b)=>b.score-a.score);
 const peerLeader=peers.length?peers[0]:null;
 const peerDelta=peerLeader?metric.agent_memory_score-peerLeader.score:null;
 const values=[['Best accepted external peer',peerLeader?pct(peerLeader.score):'Not measured',''],['Agent Memory',pct(metric.agent_memory_score),'accent'],['Agent Memory vs external peer',peerDelta===null?'No accepted peer':(peerDelta>=0?'+':'')+(100*peerDelta).toFixed(2)+' pp','']];
 $('metricSummary').innerHTML=values.map(([k,v,color])=>'<div class="metric"><div class="k">'+esc(k)+'</div><div class="v '+color+'">'+esc(v)+'</div></div>').join('');
 const rows=[...metric.rows].sort((a,b)=>b.score-a.score);
 $('leaderRows').innerHTML=rows.map(r=>{
 const dist=Math.max(0,metric.best_score-r.score);
 return '<tr><td><strong>'+esc(friendly(r.system))+'</strong></td><td class="role">'+esc(r.role)+'</td><td class="num">'+esc(pct(r.score))+'</td><td class="num">'+(r.sample_count??'—')+'</td><td class="num">'+(r.role==='baseline'?'Baseline':esc(pp(dist)))+'</td><td>'+(r.run_url?'<a href="'+esc(url(r.run_url))+'" target="_blank" rel="noopener noreferrer">Raw run ↗</a>':'Not linked')+'</td></tr>';
 }).join('');
 $('profileNotes').innerHTML='<strong>'+esc(profile.lane_id)+'</strong> / '+esc(profile.plane)+' · accepted '+esc(profile.accepted_on||'date unavailable')+' · inference calls in this lane: '+(profile.llm_calls?'yes':'no')+' · <a href="'+esc(url(profile.benchmark_file))+'" target="_blank" rel="noopener noreferrer">Pinned lane definition ↗</a> · input SHA-256 <code>'+esc(profile.input_sha256)+'</code><p>'+esc(profile.method_note||'The native metric definition and comparator budget control interpretation.')+'</p><p>Only accepted rows reporting this native metric are compared. The external peer leader excludes Agent Memory and lexical baselines. A positive Agent Memory gap means it leads that peer in this higher-is-better metric; a negative gap means it trails. One measured external product does not establish market-wide rank. No vendor-published reference is mixed into this comparison.</p>';
}
function updateMetricOptions(){
 const profile=catalog.profiles.find(p=>p.profile_id===$('profileSelect').value);
 setOptions($('metricSelect'),(profile?.metrics||[]).map(m=>({value:m.metric,label:friendly(m.metric)})));
 renderMetric();
}
function renderCompetitors(){
 const value=$('statusFilter').value;
 const records=catalog.competitors.filter(c=>value==='all'||c.state===value);
 $('competitorGrid').innerHTML=records.map(c=>'<a class="competitor" href="'+esc(url(c.url))+'" target="_blank" rel="noopener noreferrer" aria-label="'+esc(c.name+' '+stateLabel(c.state))+'"><div class="compname"><h3>'+esc(c.name)+' ↗</h3><span class="state '+esc(c.state)+'">'+esc(stateLabel(c.state))+'</span></div><p>'+(c.state==='measured'?'Accepted comparable evidence exists in at least one listed profile.':c.state==='not_run'?'Known candidate. No accepted Agent Memory same-harness comparison yet.':'Published source context only, not directly comparable.')+'</p></a>').join('')||'<p class="fineprint">No candidates match this filter.</p>';
}
function renderPublished(){
 $('publishedGrid').innerHTML=catalog.published_reference.map(r=>'<article class="reference"><span class="state published_reference">Published reference · non-comparable</span><h3 style="margin-top:15px">'+esc(r.system)+'</h3><p>'+esc(r.methodology||'External reported methodology')+'</p><p>'+Object.entries(r.signals||{}).map(([k,v])=>esc(friendly(k))+': '+esc(typeof v==='number'?pct(v):v)).join(' · ')+'</p><a href="'+esc(url(r.source))+'" target="_blank" rel="noopener noreferrer">Original source ↗</a></article>').join('');
}
function render(){
 $('snapshot').textContent='Evidence snapshot · '+catalog.source.dashboard_as_of;
 const usable=catalog.profiles.filter(p=>p.metrics.length>0);
 const n=usable.reduce((acc,p)=>acc+p.metrics.length,0);
 const peers=new Set(usable.flatMap(p=>p.metrics.flatMap(m=>m.rows.filter(r=>r.role==='comparator'&&typeof r.score==='number').map(r=>r.system.toLowerCase().replaceAll('_','-')))));
 const remaining=Math.max(0,6-peers.size);
 $('stats').innerHTML=[[''+peers.size,'Accepted external memory products'],[''+remaining,'More products needed for minimum six'],[''+n,'Comparable native metric contexts']].map(([v,k])=>'<div class="stat"><strong>'+esc(v)+'</strong><span>'+esc(k)+'</span></div>').join('');
 setOptions($('profileSelect'),usable.map(p=>({value:p.profile_id,label:friendly(p.lane_id)+' / '+friendly(p.plane)})));
 $('profileSelect').addEventListener('change',updateMetricOptions);
 $('metricSelect').addEventListener('change',renderMetric);
 $('statusFilter').addEventListener('change',renderCompetitors);
 updateMetricOptions();renderCompetitors();renderPublished();
 if (globalThis.AgentMemoryPeerEvidence?.render) {
   try { globalThis.AgentMemoryPeerEvidence.render(document,catalog); }
   catch(error) { $('coverageSummary').textContent='Coverage reporting blocked: '+error.message; }
 }
}
fetch('./data/snapshot.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Snapshot unavailable ('+r.status+')');return r.json()}).then(data=>{
 if(data.schema_version!==1||data.source?.authority_effect!=='none'||!Array.isArray(data.profiles))throw new Error('Unsupported or untrusted snapshot format');
 catalog=data;render();
}).catch(error=>{
 $('snapshot').textContent='Evidence unavailable';
 $('stats').innerHTML='<div class="error">Evidence snapshot could not be loaded. Consult the canonical GitHub dashboard.</div>';
 $('leaderRows').innerHTML='<tr><td colspan="6" class="error">'+esc(error.message)+'</td></tr>';
 $('competitorGrid').innerHTML='<p class="error">Registry unavailable. <a href="https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/806">View the evaluation plan.</a></p>';
});
