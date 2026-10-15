/* Stable public benchmark measurement feed v1.
 * Layout-independent: validated measurement records update existing leaderboard controls.
 * The feed's numbers are computed from immutable, SHA256-verified native artifacts;
 * no feed row can claim acceptance or create a cross-cohort ranking.
 */
(function(root){
'use strict';
const REPO='MythologIQ-Labs-LLC/agent-memory';
const BRANCH='benchmark-public-feed';
const PATH='reports/benchmarks/public-feed/v1.json';
const API='https://api.github.com/repos/'+REPO;
const RAW='https://raw.githubusercontent.com/'+REPO+'/';
const ID=/^[a-zA-Z0-9_][a-zA-Z0-9_.:@-]{1,149}$/;
const SHA=/^[0-9a-f]{40}$/;
const SHA256=/^[0-9a-f]{64}$/;
const ARTIFACT=/^reports\/benchmarks\/[a-zA-Z0-9_./-]+\.(?:json|json\.gz|csv)$/;
const MAX_RECORDS=120;
const MAX_PROFILES=36;
const MAX_BYTES=8*1024*1024;
const validArtifact=p=>typeof p==='string'&&ARTIFACT.test(p)&&
  p.split('/').every(seg=>seg!=='.'&&seg!=='..'&&seg!=='');
const validScore=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0&&n<=1;
function validate(feed){
 if(!feed||feed.kind!=='agent-memory-measured-results-feed'||feed.schema_version!==1||
   feed.authority_effect!=='none'||!Array.isArray(feed.profiles)||
   feed.profiles.length===0||feed.profiles.length>MAX_PROFILES)throw Error('Invalid feed envelope');
 const ids=new Set();
 let count=0;
 for(const p of feed.profiles) {
  if(!p||!ID.test(p.id||'')||ids.has(p.id)||!ID.test(p.family||'')||
     typeof p.title!=='string'||!p.title||p.title.length>200||
     typeof p.protocol!=='string'||!p.protocol||p.protocol.length>500||
     typeof p.evaluator_revision!=='string'||!p.evaluator_revision||
     typeof p.metric!=='string'||!p.metric||
     typeof p.method_note!=='string'||!p.method_note||
     p.method_note.length>1800||
     !['candidate','reproduced','reviewed_self_run_unofficial'].includes(p.evidence_status)||
     !p.cohort||!Number.isInteger(p.cohort.sample_count)||
     !Number.isInteger(p.cohort.scored_count)||
     !Number.isInteger(p.cohort.excluded_count)||
     p.cohort.sample_count<1||p.cohort.scored_count<1||
     p.cohort.scored_count+p.cohort.excluded_count!==p.cohort.sample_count||
     !SHA256.test(p.cohort.input_sha256||'')||
     typeof p.cohort.selection_id!=='string'||!p.cohort.selection_id||
     !Array.isArray(p.rows)||p.rows.length<1||p.rows.length>45)
    throw Error('Invalid benchmark profile: '+(p?.id||'unknown'));
  ids.add(p.id);
  const systems=new Set();
  for(const row of p.rows) {
   count++;
   if(count>MAX_RECORDS||!row||!ID.test(row.system||'')||
      systems.has(row.system)||typeof row.label!=='string'||!row.label||row.label.length>140||
      !['control','comparator','baseline'].includes(row.role)||
      row.status!==p.evidence_status||!SHA.test(row.source_commit||'')||
      !validArtifact(row.artifact)||!SHA256.test(row.artifact_sha256||'')||
      !row.extract||!validScore(row.expected_score)||
      (row.engine_revision!=null&&!SHA.test(row.engine_revision))||
      (row.revision_path!=null&&(!Array.isArray(row.revision_path)||
        row.revision_path.length<1||row.revision_path.length>9||
        row.revision_path.some(k=>typeof k!=='string'||!k||
          ['__proto__','prototype','constructor'].includes(k)))))
     throw Error('Invalid public measurement source for '+p.id);
   systems.add(row.system);
   if(row.extract.type==='json_path'){
    if(!row.artifact.endsWith('.json')&&!row.artifact.endsWith('.json.gz'))
     throw Error('JSON extract requires JSON artifact');
    if(!Array.isArray(row.extract.path)||row.extract.path.length<1||
       row.extract.path.length>12||row.extract.path.some(k=>
         typeof k!=='string'||!k||k.length>100||['__proto__','prototype','constructor'].includes(k)))
     throw Error('Invalid native JSON path');
   } else if(row.extract.type==='csv_correct_fraction'){
    if(!row.artifact.endsWith('.csv')||row.extract.column!=='correct'||
       row.extract.pass_value!=='True')throw Error('Unsupported native CSV scoring');
   } else throw Error('Unrecognized native evaluator extractor');
  }
 }
 return feed;
}
function jsonValue(document,path){
 let current=document;
 for(const key of path){
  if(!current||typeof current!=='object'||
     !Object.prototype.hasOwnProperty.call(current,key))throw Error('Native metric path missing');
  current=current[key];
 }
 if(!validScore(current))throw Error('Native metric outside 0..1');
 return current;
}
function jsonValueText(document,path){
 let current=document;
 for(const key of path){if(!current||typeof current!=='object'||
   !Object.prototype.hasOwnProperty.call(current,key))throw Error('Runtime identity missing');
   current=current[key];}
 if(typeof current!=='string')throw Error('Runtime identity not a string');
 return current;
}
function csvVerdicts(raw){
 if(typeof raw!=='string'||raw.length>MAX_BYTES)throw Error('Invalid native CSV');
 const rows=[];let fields=[],token='',quoted=false;
 for(let i=0;i<raw.length;i++){
  const c=raw[i];
  if(c==='"'){if(quoted&&raw[i+1]==='"'){token+='"';i++;}else quoted=!quoted;}
  else if(c===','&&!quoted){fields.push(token);token='';}
  else if((c==='\n'||c==='\r')&&!quoted){
   if(c==='\r'&&raw[i+1]==='\n')i++;
   fields.push(token);token='';
   if(fields.length>1)rows.push(fields);
   fields=[];
  }else token+=c;
 }
 if(quoted)throw Error('Malformed quoted CSV');
 if(token||fields.length){fields.push(token);rows.push(fields);}
 const header=rows.shift();
 if(!header||header.filter(x=>x==='correct').length!==1||
    !header.includes('query_id')||new Set(header).size!==header.length)
   throw Error('Missing native correctness columns');
 const ix=header.indexOf('correct'),id=header.indexOf('query_id'),seen=new Set();
 let correct=0;
 for(const row of rows){
  if(row.length!==header.length||!row[id]||seen.has(row[id])||
     !['True','False'].includes(row[ix]))throw Error('Malformed or duplicate native verdict');
  seen.add(row[id]);
  if(row[ix]==='True')correct++;
 }
 if(!rows.length)throw Error('Empty native result');
 return {sample_count:rows.length,scored_count:rows.length,correct,score:correct/rows.length};
}
function evaluate(profile,row,raw){
 if(row.extract.type==='csv_correct_fraction'){
  const result=csvVerdicts(raw);
  if(result.sample_count!==profile.cohort.sample_count||
     profile.cohort.scored_count!==result.scored_count)
    throw Error('Native CSV population mismatch');
  return result.score;
 }
 let data;
 try{data=JSON.parse(raw);}catch(e){throw Error('Native JSON unavailable');}
 if(row.engine_revision&&row.revision_path&&
    jsonValueText(data,row.revision_path)!==row.engine_revision)
   throw Error('Runtime revision identity mismatch');
 if(profile.family==='longmemeval-s-retrieval'){
  if(data.input?.sha256!==profile.cohort.input_sha256||
     data.input?.question_count!==profile.cohort.sample_count)
    throw Error('Native LongMemEval dataset mismatch');
  const expected=/ids_sha256=([0-9a-f]{64})/.exec(profile.cohort.selection_id)?.[1];
  if(!expected||data.input?.selection?.question_ids_sha256!==expected)
    throw Error('Native LongMemEval selection mismatch');
  const path=row.extract.path;
  if(path[0]!=='planes'||!['session','turn'].includes(path[1])||
    path[2]!=='backends'||path[4]!=='aggregate'||path[5]!=='headline'||
    path[6]!==profile.metric)
   throw Error('Unexpected native evaluator path');
  const result=data.planes?.[path[1]]?.backends?.[path[3]];
  if(!result||!result.failures||
    ['runtime_failure_count','ingestion_failure_count','out_of_corpus_returned_count']
      .some(k=>result.failures[k]!==0)||
    result.aggregate?.evaluated_question_count!==profile.cohort.scored_count||
    result.aggregate?.excluded_abstention_count+
      result.aggregate?.excluded_no_user_target_count!==profile.cohort.excluded_count)
   throw Error('Native errors or denominator mismatch');
 }
 return jsonValue(data,row.extract.path);
}
function urlAt(sha,path){
 if(!SHA.test(sha)||!validArtifact(path))throw Error('Unsafe immutable artifact path');
 return RAW+sha+'/'+path;
}
async function verify(data,digest){
 if(!root.crypto?.subtle)throw Error('Browser SHA-256 verification unavailable');
 const b=await root.crypto.subtle.digest('SHA-256',data);
 const sha=Array.from(new Uint8Array(b)).map(x=>x.toString(16).padStart(2,'0')).join('');
 if(sha!==digest)throw Error('Native artifact SHA-256 mismatch');
}
async function readArtifact(row){
 const resp=await fetch(urlAt(row.source_commit,row.artifact),{cache:'no-store'});
 if(!resp.ok)throw Error('Source artifact HTTP '+resp.status);
 const data=await resp.arrayBuffer();
 if(data.byteLength>MAX_BYTES)throw Error('Native artifact exceeds public-feed cap');
 await verify(data,row.artifact_sha256);
 if(row.artifact.endsWith('.gz')){
  if(typeof DecompressionStream==='undefined')throw Error('Browser gzip support unavailable');
  return new Response(new Blob([data]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
 }
 return new TextDecoder().decode(data);
}
function toProfile(group,rankedRows,sha){
 return {id:group.id,title:group.title,family:group.family,
  evidence_status:group.evidence_status,origin:'Versioned public measurement feed · SHA '+sha.slice(0,12),
  method_note:group.method_note+' Cohort '+group.cohort.scored_count+
   '/'+group.cohort.sample_count+' scored, '+group.cohort.excluded_count+
   ' excluded. Native result bytes SHA-256 verified. Protocol: '+group.protocol,
  metrics:[{metric:group.metric,rows:rankedRows}]};
}
async function processFeed(feed,sourceSha){
 validate(feed);
 if(!SHA.test(sourceSha))throw Error('Invalid source commit');
 const cache=new Map(),profiles=[],errors=[];
 for(const group of feed.profiles){
  const rows=[];
  for(const row of group.rows){
   try{
    const key=row.source_commit+'/'+row.artifact;
    let text;
    if(cache.has(key)){
     const cached=cache.get(key);
     if(cached.digest!==row.artifact_sha256)throw Error('Artifact digest conflict');
     text=cached.text;
    }else{
     text=await readArtifact(row);
     cache.set(key,{text,digest:row.artifact_sha256});
    }
    const actual=evaluate(group,row,text);
    if(Math.abs(actual-row.expected_score)>0.000001)throw Error('Declared score differs from native evaluator');
    rows.push({system:row.system,label:row.label,role:row.role,
     score:actual,sample_count:group.cohort.scored_count,
     status:row.status,run_url:'https://github.com/'+REPO+'/blob/'+
       row.source_commit+'/'+row.artifact});
   }catch(e){errors.push(group.id+'/'+row.system+': '+e.message);}
  }
  if(rows.length>=2||rows.length===1&&group.rows.length===1)
    profiles.push(toProfile(group,rows,sourceSha));
 }
 return {profiles,errors};
}
let currentHead=null,profileCache=[],started=false;
async function refresh(){
 const ref=await fetch(API+'/git/ref/heads/'+BRANCH,{cache:'no-store',
   headers:{Accept:'application/vnd.github+json'}});
 if(!ref.ok)throw Error('Public feed ref status '+ref.status);
 const refDoc=await ref.json(),head=refDoc?.object?.sha;
 if(!SHA.test(head))throw Error('Invalid public feed ref');
 if(currentHead===head)return profileCache;
 const data=await fetch(RAW+head+'/'+PATH,{cache:'no-store'});
 if(!data.ok)throw Error('Public benchmark feed unavailable: '+data.status);
 const result=await processFeed(await data.json(),head);
 // No automatic fallback to unverifiable results: keep previously validated feed
 // until the next complete branch update.
 if(!result.profiles.length)throw Error('No verifiable public measurements');
 currentHead=head;
 profileCache=result.profiles;
 if(typeof root.dispatchEvent==='function'&&typeof CustomEvent!=='undefined')
  root.dispatchEvent(new CustomEvent('agent-memory:public-feed',
    {detail:{profiles:profileCache,head,errors:result.errors}}));
 return profileCache;
}
function attach(){
 if(started)return;started=true;
 refresh().catch(()=>{}); // The existing pinned candidate backup remains visible.
 document.getElementById('liveRefresh')?.addEventListener('click',()=>refresh().catch(()=>{}));
 setInterval(()=>{if(document.visibilityState==='visible')refresh().catch(()=>{});},15*60*1000);
}
root.AgentMemoryPublicFeed={validate,jsonValue,csvVerdicts,evaluate,processFeed,refresh,
 getLastProfiles:()=>profileCache.slice(),getLastHead:()=>currentHead};
if(typeof module!=='undefined'&&module.exports)module.exports=root.AgentMemoryPublicFeed;
if(typeof document!=='undefined'){
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',attach,{once:true});
 else attach();
}
})(typeof window!=='undefined'?window:globalThis);
