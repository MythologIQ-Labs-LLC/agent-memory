export const SAFE_METRICS = ["mean_precision","mean_recall","recall_all@5","recall_all@10","ndcg_any@5","ndcg_any@10","knowledge_update_recall_all@5","latest_gold_ranked_first"];

function norm(x){return String(x||"").trim().toLowerCase().replaceAll("_","-")}

function validatePath(x){if(typeof x!=="string"||x.startsWith("/")||x.includes("..")||!/^[-\w/.]+$/.test(x))throw Error("Untrusted evidence path: "+x);return x}

export function sampleInfo(row,laneId){
 const n=row.native?.scored_questions;
 if(Number.isSafeInteger(n)&&n>0)return {value:n,source:"native.scored_questions"};
 if(String(laneId).startsWith("amb-precisionmembench-")){
  const m=/^([0-9]+)\/([0-9]+)$/.exec(String(row.native?.total_passes||""));
  if(m){
   const passed=Number(m[1]),total=Number(m[2]);
   if(Number.isSafeInteger(total)&&total>0&&passed<=total){
    return {value:total,source:"native.total_passes denominator; confirmed against accepted AMB query_count"};
   }
  }
 }
 return {value:null,source:"not_available_in_dashboard"};
}

export function makeSnapshot(d,c,o){
 if(!d||d.schema_version!==2||d.authority_effect!=="none"||!d.as_of||!Array.isArray(d.competitive_evidence?.frozen_lanes))throw Error("Canonical dashboard contract mismatch");
 if(!c||c.schema_version!==1||!Array.isArray(c.systems))throw Error("Comparator registry contract mismatch");
 if(!/^[0-9a-f]{40}$/.test(o.head)||!/^[0-9a-f]{40}$/.test(o.blob))throw Error("Immutable source head/blob required");
 const accepted=d.competitive_evidence.frozen_lanes.filter(x=>x.status==="accepted");
 const observed=new Set(accepted.flatMap(x=>(x.accepted_rows||[]).filter(z=>z.role!=="baseline").map(z=>norm(z.provider))));
 const profiles=[];
 for(const lane of accepted){
  if(!lane.lane_id||!lane.input_sha256||!lane.harness_revision||!lane.lane_file)throw Error("Incomplete accepted lane identity");
  const groups=new Map();
  for(const row of lane.accepted_rows||[]){
   if(!row.provider||!row.role||!row.system_revision||!row.evidence||!row.native)throw Error("Missing accepted run provenance");
   const plane=row.plane||"single-turn";
   if(!groups.has(plane))groups.set(plane,[]);
   groups.get(plane).push(row);
  }
  for(const [plane,items] of groups){
   const metrics=[];
   for(const key of SAFE_METRICS){
    const rows=items.filter(x=>typeof x.native[key]==="number").map(x=>{
     const score=x.native[key];
     if(!Number.isFinite(score)||score<0||score>1)throw Error("Invalid fraction-valued metric "+key);
     const sample=sampleInfo(x,lane.lane_id);
     return {system:x.provider,role:x.role,score,revision:x.system_revision,run_url:"https://github.com/"+o.repo+"/blob/"+o.head+"/"+validatePath(x.evidence),sample_count:sample.value,sample_count_source:sample.source,workflow_run_id:x.workflow_run_id??null};
    });
    const control=rows.find(x=>x.role==="control");
    if(!control||rows.length<2)continue;
    const ranked=rows.filter(x=>x.role!=="baseline").sort((a,b)=>b.score-a.score);
    const best=ranked[0];
    metrics.push({metric:key,direction:"higher",metric_unit:"fraction",best_score:best.score,best_system:best.system,agent_memory_score:control.score,gap_to_best:+Math.max(0,best.score-control.score).toFixed(6),rows});
   }
   if(metrics.length)profiles.push({profile_id:lane.lane_id+(plane!=="single-turn"?":"+plane:""),lane_id:lane.lane_id,plane,accepted_on:lane.accepted_on||null,benchmark_file:"https://github.com/"+o.repo+"/blob/"+o.head+"/"+validatePath(lane.lane_file),input_sha256:lane.input_sha256,harness_revision:lane.harness_revision,llm_calls:lane.llm_calls===true,method_note:lane.reading_rule||lane.note||"",metrics});
  }
 }
 const ids=new Set(), competitors=[];
 for(const citem of c.systems){
  if(!/^[a-z0-9][a-z0-9-]*$/.test(citem.id)||ids.has(citem.id)||!citem.name||!/^https:\/\//.test(citem.url))throw Error("Invalid or duplicate comparator entry "+citem.id);
  ids.add(citem.id);
  if(!["measured","not_run","published_reference"].includes(citem.state))throw Error("Unexpected comparator state");
  const aliases=(citem.observed_ids||[]).map(norm),hasEvidence=aliases.some(x=>observed.has(x));
  if(citem.state==="measured"&&!hasEvidence)throw Error("Measured system lacks accepted evidence: "+citem.id);
  if(citem.state==="not_run"&&hasEvidence)throw Error("System marked not_run has accepted evidence: "+citem.id);
  competitors.push({id:citem.id,name:citem.name,state:citem.state,url:citem.url,observed_ids:citem.observed_ids||[]});
 }
 if(!ids.has("tencentdb-agent-memory"))throw Error("TencentDB comparator missing");
 const published=(d.published_reference||[]).map(x=>({...x,comparison_state:"published_reference",eligible_for_numeric_delta:false}));
 return {schema_version:1,kind:"static_read_only_benchmark_projection",source:{repository:"https://github.com/"+o.repo,head:o.head,dashboard_path:"reports/benchmarks/dashboard/current.json",dashboard_blob:o.blob,dashboard_as_of:d.as_of,authority_effect:"none"},safety:{same_harness:"Comparisons only within one accepted frozen lane, plane and native metric.",published_reference:"Vendor/research figures are not same-harness results.",not_run:"Not run is not zero.",runtime_qualification:"Benchmark scores are not production readiness, truth or authority.",no_universal_score:true},profiles,competitors,published_reference:published,issues:{competitive:"https://github.com/"+o.repo+"/issues/806",website:"https://github.com/"+o.repo+"/issues/807"}};
}

import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
const flags=Object.fromEntries(process.argv.slice(2).reduce((pairs,arg,i,all)=>{if(arg.startsWith('--')&&arg!=='--check')pairs.push([arg.slice(2),all[i+1]]);return pairs},[]));
const check=process.argv.includes('--check');
if(!flags.dashboard||!flags.competitors||!flags.out||!flags['source-head']){console.error('Usage: node tools/build-site-data.mjs --dashboard PATH --competitors config/competitors.json --out data/snapshot.json --source-head COMMIT [--check]');process.exit(2)}
if(!/^[0-9a-f]{40}$/.test(flags['source-head']))throw Error('source-head must be full 40-char SHA');
const dashboardBytes=fs.readFileSync(flags.dashboard);
const digest=execFileSync('git',['hash-object',flags.dashboard],{encoding:'utf8'}).trim();
const dash=JSON.parse(dashboardBytes.toString('utf8'));
const competitors=JSON.parse(fs.readFileSync(flags.competitors,'utf8'));
const out=JSON.stringify(makeSnapshot(dash,competitors,{repo:'MythologIQ-Labs-LLC/agent-memory',head:flags['source-head'],blob:digest}),null,2)+'\n';
if(check){if(!fs.existsSync(flags.out)||fs.readFileSync(flags.out,'utf8')!==out){console.error('STALE generated benchmark snapshot: '+flags.out);process.exit(1)}console.log('PASS: snapshot matches pinned canonical dashboard');}
else{fs.writeFileSync(flags.out,out);console.log('Generated '+flags.out)}
}
