/* Candidate run auto-discovery from standard issue-808 execution manifests.
 * Accepted leaderboard is NEVER read or modified here.
 * No repo branches scanned outside the explicitly versioned source allowlist.
 */
(function(root) {
'use strict';
const REPO='MythologIQ-Labs-LLC/agent-memory';
const API='https://api.github.com/repos/'+REPO;
const RAW='https://raw.githubusercontent.com/'+REPO;
const SHA=/^[a-f0-9]{40}$/;
const DIGEST=/^[a-f0-9]{64}$/;
const SAFE_PATH=/^reports\/benchmarks\/runs\/[a-zA-Z0-9_./-]+$/;
const MAX_BODY=8*1024*1024;
const html=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cleanPath=p=>typeof p==='string'&&SAFE_PATH.test(p)&&!p.split('/').includes('..')&&!p.includes('//');
const number=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0&&x<=1;
const format=n=>(100*n).toFixed(2)+'%';
const evidenceLink=(sha,p,label)=>'<a href="https://github.com/'+REPO+'/blob/'+sha+'/'+
  html(p)+'" target="_blank" rel="noopener noreferrer">'+html(label)+' ↗</a>';
function validateSources(config){
  if(!config||config.schema_version!==1||config.kind!=='public-candidate-manifest-sources'||
     config.authority_effect!=='none'||config.repository!==REPO||config.read_only!==true||
     !Array.isArray(config.sources)||config.sources.length<1||config.sources.length>4)
    throw Error('Invalid read-only source allowlist');
  const seen=new Set();
  for(const src of config.sources) {
    if(!/^[a-zA-Z0-9_.-]+(?:\/[a-zA-Z0-9_.-]+)*$/.test(src.branch)||seen.has(src.branch)||
       src.prefix!=='reports/benchmarks/runs/'||
       !Number.isInteger(src.max_manifest_files)||src.max_manifest_files>48||
       src.max_manifest_files<1||!Number.isInteger(src.max_partial_files)||
       src.max_partial_files>24||src.max_partial_files<0)throw Error('Invalid source limit or path');
    seen.add(src.branch);
  }
  return config.sources;
}
function validateManifest(m,path) {
  if(!cleanPath(path)||!path.endsWith('.manifest.json')||!m||
      m.schema_version!=='1.0.0'||m.authority_effect!=='none'||
      typeof m.run_id!=='string'||!m.run_id||
      !m.benchmark||typeof m.benchmark.id!=='string'||
      typeof m.benchmark.task_profile!=='string'||
      !DIGEST.test(m.benchmark.input_sha256||'')||
      !Number.isInteger(m.benchmark.sample_count)||m.benchmark.sample_count<1||
      !Number.isInteger(m.benchmark.excluded_count)||m.benchmark.excluded_count<0||
      m.benchmark.excluded_count>m.benchmark.sample_count||
      !m.normalized_run||!cleanPath(m.normalized_run.uri)||
      !DIGEST.test(m.normalized_run.sha256||'')||
      !m.system||!m.system.id||!m.system.adapter_revision||
      !m.execution||m.execution.exit_code!==0||
      !m.review||!['candidate','reproduced','reviewed'].includes(m.review.status)||
      m.review.comparison_eligibility==='accepted') throw Error('Ineligible source manifest');
  const last=path.split('/').pop();
  const match=/^(session|turn)\.([a-zA-Z0-9_-]+)\.manifest\.json$/.exec(last);
  if(!match||!m.benchmark.task_profile.endsWith(':'+match[1])||
    !m.run_id.endsWith(':'+match[1]+':'+match[2]))throw Error('Manifest plane/backend conflict');
  if(!m.normalized_run.uri.startsWith('reports/benchmarks/runs/'))
    throw Error('Manifest normalized run outside allowed root');
  return {plane:match[1],backend:match[2]};
}
function validateSummary(m,path){
  if(!cleanPath(path)||!path.endsWith('.summary.json')||!m||!m.aggregate||
     m.question_count_preregistered!==50||
     !Number.isInteger(m.question_count_completed)||m.question_count_completed<0||
     m.question_count_completed>50||
     !Number.isInteger(m.aggregate.evaluated_question_count)||
     m.aggregate.evaluated_question_count>m.question_count_completed||
     !Array.isArray(m.missing_question_ids)||
     m.missing_question_ids.length!==50-m.question_count_completed||
     !m.failures||!['runtime_failure_count','ingestion_failure_count','out_of_corpus_returned_count']
       .every(k=>m.failures[k]===0))throw Error('Unqualified partial progress source');
  const match=/^(session|turn)\.([a-zA-Z0-9_-]+)\.summary\.json$/.exec(path.split('/').pop());
  if(!match) throw Error('Unknown partial result filename');
  return {plane:match[1],backend:match[2],completed:m.question_count_completed,
    scored:m.aggregate.evaluated_question_count,planned:50};
}
function extractMetric(report,manifest,identity) {
  if(report?.input?.sha256!==manifest.benchmark.input_sha256||
     report?.input?.question_count!==manifest.benchmark.sample_count)throw Error('Report input does not match manifest');
  const sel=manifest.benchmark.selection_id;
  if(typeof sel==='string'){
    const match=/ids_sha256=([a-f0-9]{64})/.exec(sel);
    if(match&&report?.input?.selection?.question_ids_sha256!==match[1])
      throw Error('Question selection mismatch');
  }
  const row=report?.planes?.[identity.plane]?.backends?.[identity.backend];
  if(!row||!row.aggregate||!row.failures||
     !['runtime_failure_count','ingestion_failure_count','out_of_corpus_returned_count']
       .every(k=>row.failures[k]===0)) throw Error('Missing or failed native report plane');
  const agg=row.aggregate;
  if(!Number.isInteger(agg.evaluated_question_count)||
     !Number.isInteger(agg.excluded_abstention_count)||
     !Number.isInteger(agg.excluded_no_user_target_count)||
     agg.evaluated_question_count+
       agg.excluded_abstention_count+agg.excluded_no_user_target_count!==
         manifest.benchmark.sample_count||
     agg.excluded_abstention_count+agg.excluded_no_user_target_count!==
         manifest.benchmark.excluded_count)throw Error('Native denominator mismatch');
  if(manifest.benchmark.id!=='longmemeval-s-retrieval')return null; // unsupported family: show provenance, no assumed score
  const metric=identity.plane==='session'?'recall_all@5':'recall_all@10';
  const score=agg.headline?.[metric];
  if(!number(score))throw Error('Native metric missing or out of range');
  return {metric,score,scored:agg.evaluated_question_count,excluded:manifest.benchmark.excluded_count};
}
function listFiles(tree,config){
  if(!tree||tree.truncated!==false||!Array.isArray(tree.tree))
    throw Error('GitHub tree truncated or missing; refusing incomplete source discovery');
  const blobs=tree.tree.filter(e=>e.type==='blob'&&e.path.startsWith(config.prefix)&&
    cleanPath(e.path)&&Number.isInteger(e.size)&&e.size>=0);
  const manifest=blobs.filter(e=>e.path.endsWith('.manifest.json')&&e.size<=16000);
  const partial=blobs.filter(e=>e.path.endsWith('.summary.json')&&e.size<=20000);
  if(manifest.length>config.max_manifest_files||partial.length>config.max_partial_files)
    throw Error('Source file discovery exceeds audited caps; manual review required');
  return {manifest:manifest.map(x=>x.path).sort(),partial:partial.map(x=>x.path).sort(),
    known:new Map(blobs.map(x=>[x.path,x.size]))};
}
async function jsonFetch(url) {
  const response=await fetch(url,{cache:'no-store',headers:{Accept:'application/vnd.github+json'}});
  if(!response.ok)throw Error('Source API HTTP '+response.status);
  return response.json();
}
async function locate(src){
  const branch=src.branch.split('/').map(encodeURIComponent).join('/');
  const ref=await jsonFetch(API+'/git/ref/heads/'+branch);
  const sha=ref?.object?.sha;
  if(!SHA.test(sha))throw Error('Branch head is not a commit SHA');
  const commit=await jsonFetch(API+'/git/commits/'+sha);
  if(!SHA.test(commit?.tree?.sha))throw Error('Commit missing content tree');
  const tree=await jsonFetch(API+'/git/trees/'+commit.tree.sha+'?recursive=1');
  return {sha,files:listFiles(tree,src)};
}
function rawUrl(sha,p) {
  if(!SHA.test(sha)||!cleanPath(p))throw Error('Invalid immutable report locator');
  return RAW+'/'+sha+'/'+p;
}
async function bytesAt(sha,p,knownSize){
  if(!Number.isInteger(knownSize)||knownSize>MAX_BODY||knownSize<1)
    throw Error('Large or untracked normalized run');
  const resp=await fetch(rawUrl(sha,p),{cache:'no-store'});
  if(!resp.ok)throw Error('Evidence download HTTP '+resp.status);
  const bytes=await resp.arrayBuffer();
  if(bytes.byteLength!==knownSize)throw Error('Evidence byte count mismatch');
  return bytes;
}
async function verifyBytes(bytes,expected){
  if(!DIGEST.test(expected)||typeof crypto==='undefined'||!crypto.subtle)
    throw Error('SHA-256 browser verification unavailable');
  const hash=await crypto.subtle.digest('SHA-256',bytes);
  const found=Array.from(new Uint8Array(hash)).map(x=>x.toString(16).padStart(2,'0')).join('');
  if(found!==expected)throw Error('Report SHA-256 does not match manifest');
}
async function toText(bytes,compressed) {
  if(compressed) {
    if(typeof DecompressionStream==='undefined')throw Error('Browser cannot inspect gzip evidence');
    const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Response(stream).text();
  }
  return new TextDecoder().decode(bytes);
}
const LABELS={agent_memory:'Agent Memory control',lexical_overlap:'Lexical baseline',
  mem0:'Mem0 OSS',hindsight:'Hindsight'};
function nameFor(id) {return LABELS[id]||String(id).replace(/[_-]/g,' ').replace(/\b\w/g,x=>x.toUpperCase());}
function cohort(m){return m.benchmark.sample_count+' input · '+
    (m.benchmark.selection_id?.startsWith('all|')?'full':'preregistered subset');}
function createRow(m,path,sha,identity,metric,error) {
  return {kind:'manifest',name:nameFor(m.system.id),benchmark:m.benchmark.id,
    cohort:cohort(m),plane:identity.plane,metric:metric?.metric||null,
    score:metric?.score??null,coverage:metric
      ?metric.scored+'/'+m.benchmark.sample_count+' scored · '+metric.excluded+' excluded'
      :'Evidence score withheld ('+String(error||'unsupported native metric')+')',
    manifestPath:path,runPath:m.normalized_run.uri,
    review:m.review.status,sha};
}
function createPartial(path,sha,info){
  return {kind:'partial',name:nameFor(info.backend),benchmark:'longmemeval-s-retrieval',
    cohort:'50 input · preregistered subset',plane:info.plane,metric:null,score:null,
    coverage:info.completed+'/'+info.planned+' completed · '+
      info.scored+' scored so far · no aggregate',manifestPath:path,runPath:path,
    review:'candidate progress',sha};
}
function render(rows,updated,sources,problems) {
  const target=document.getElementById('discoveredRunRows');
  const status=document.getElementById('discoveredRunStatus');
  if(!target||!status)return;
  const limited=rows.slice(0,70);
  const header='<thead><tr><th>Memory system</th><th>Benchmark / cohort</th><th>Plane</th>'+
    '<th>Native result</th><th>Coverage</th><th>Commit-pinned evidence</th></tr></thead>';
  const body=limited.map(r=>'<tr><th scope="row">'+html(r.name)+
    '<span class="discover-review">'+html(r.review)+'</span></th><td>'+html(r.benchmark)+
    '<small>'+html(r.cohort)+'</small></td><td>'+html(r.plane)+'</td><td>'+
    (r.score===null?'<span class="live-unknown">Not reportable</span>':
      '<strong class="live-number">'+html(format(r.score))+'</strong><small>'+
      html(r.metric)+'</small>')+'</td><td>'+html(r.coverage)+'</td><td>'+
    evidenceLink(r.sha,r.manifestPath,'Manifest')+'<small>'+
    html(r.sha.slice(0,12))+'</small></td></tr>').join('');
  target.innerHTML=body?'<table class="discover-table">'+header+'<tbody>'+body+'</tbody></table>':
    '<p class="live-loading">No independently verifiable candidate manifests found.</p>';
  status.textContent='Read-only manifest discovery · '+limited.length+
    ' source-plane records · '+sources+' tracked source branches · checked '+updated+
    (problems.length?' · '+problems.length+' validation concern(s)':'');
  const note=document.getElementById('discoveredRunProblems');
  if(note) note.textContent=problems.length
    ?'Some evidence was withheld: '+problems.slice(0,3).join(' | ')+
      (problems.length>3?' | additional concerns omitted':'')
    :'New run manifests are discovered automatically within approved public source branches. All rows are candidate evidence, not leaderboard acceptance.';
}
let busy=false,oldHeads=new Map(),lastRows=[],sourceCache=new Map();
async function refresh(force=false) {
  if(busy)return;busy=true;
  const problems=[],rows=[];
  try {
    const config=await jsonFetch('./data/live-sources.json');
    const sources=validateSources(config);
    for(const src of sources) {
      try {
        // Branch ref is the one cheap freshness request on subsequent checks.
        const branch=src.branch.split('/').map(encodeURIComponent).join('/');
        const ref=await jsonFetch(API+'/git/ref/heads/'+branch);
        const sha=ref?.object?.sha;
        if(!SHA.test(sha))throw Error('Invalid branch SHA');
        if(!force&&oldHeads.get(src.branch)===sha&&sourceCache.has(src.branch)) {
          rows.push(...sourceCache.get(src.branch));continue;
        }
        const commit=await jsonFetch(API+'/git/commits/'+sha);
        if(!SHA.test(commit?.tree?.sha))throw Error('Invalid source commit tree');
        const tree=await jsonFetch(API+'/git/trees/'+commit.tree.sha+'?recursive=1');
        const files=listFiles(tree,src);
        const cache=new Map();
        const branchRows=[];
        for(const path of files.manifest) {
          try {
            const m=await (await fetch(rawUrl(sha,path),{cache:'no-store'})).json();
            const identity=validateManifest(m,path);
            let record=cache.get(m.normalized_run.uri);
            if(!record) {
              const bytes=await bytesAt(sha,m.normalized_run.uri,files.known.get(m.normalized_run.uri));
              await verifyBytes(bytes,m.normalized_run.sha256);
              record={sha256:m.normalized_run.sha256,data:JSON.parse(await toText(bytes,m.normalized_run.uri.endsWith('.gz')))};
              cache.set(m.normalized_run.uri,record);
            } else if(record.sha256!==m.normalized_run.sha256)throw Error('Conflicting manifest report digests');
            let metric=null,error=null;
            try {metric=extractMetric(record.data,m,identity);} catch(e){error=e.message;}
            branchRows.push(createRow(m,path,sha,identity,metric,error));
            if(error)problems.push(m.run_id+': '+error);
          }catch(e){problems.push('Invalid source manifest '+path+': '+e.message);}
        }
        for(const path of files.partial){
          try{
            const m=await (await fetch(rawUrl(sha,path),{cache:'no-store'})).json();
            const info=validateSummary(m,path);
            branchRows.push(createPartial(path,sha,info));
          }catch(e){problems.push('Partial source '+path+': '+e.message);}
        }
        oldHeads.set(src.branch,sha);
        sourceCache.set(src.branch,branchRows);
        rows.push(...branchRows);
      }catch(e){problems.push(src.branch+': '+e.message);
        if(sourceCache.has(src.branch))rows.push(...sourceCache.get(src.branch));
      }
    }
    rows.sort((a,b)=>(a.benchmark+'|'+a.cohort+'|'+a.plane+'|'+a.name)
      .localeCompare(b.benchmark+'|'+b.cohort+'|'+b.plane+'|'+b.name));
    lastRows=rows;
    render(rows,new Date().toLocaleTimeString(),sources.length,problems);
  }catch(e){
    const status=document.getElementById('discoveredRunStatus');
    if(status)status.textContent='Manifest source discovery unavailable: '+e.message+
      '. Previously accepted leaderboard data is unaffected.';
  } finally {busy=false;}
}
root.AgentMemoryRunDiscovery={validateSources,validateManifest,validateSummary,extractMetric,
  listFiles,createRow,createPartial,rawUrl,refresh};
if(typeof module!=='undefined'&&module.exports)module.exports=root.AgentMemoryRunDiscovery;
if(typeof document!=='undefined'){
 const start=()=>{
   refresh();
   document.getElementById('liveRefresh')?.addEventListener('click',()=>refresh());
   setInterval(()=>{if(document.visibilityState==='visible')refresh();},15*60*1000);
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
 else start();
}
})(typeof window!=='undefined'?window:globalThis);
