/* Read-only live execution evidence. This is NOT the accepted leaderboard.
   Reads public commits directly so new Claude evidence commits appear without Pages CI. */
(function (root) {
'use strict';
const REPO = 'MythologIQ-Labs-LLC/agent-memory';
const API = 'https://api.github.com/repos/' + REPO;
const RAW = 'https://raw.githubusercontent.com/' + REPO;
const SHA = /^[0-9a-f]{40}$/;
const INPUT_SHA = 'd6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442';
const SELECTION_SHA = '5266568e2e883b64e92e0da632d5e24c3fd61d8a447de7e629ebf93ef26a7339';
const COMP_BRANCH = 'claude/817-jev-mem-execution-no-ci';
const EXTERNAL_BRANCH = 'claude/wizardly-cray-bmkfrr';
const ROOT = 'reports/benchmarks/runs/';
const AMB = 'reports/benchmarks/amb-local-execution/2026-10-15-precisionmembench-single-turn/';
const MEMORYARENA = 'reports/benchmarks/memoryarena-local/2026-10-15-phys-task19/results/';
const ESC = c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]);
const esc = x => String(x ?? '').replace(/[&<>"']/g,ESC);
const makeUrl = (sha, path) => {
  if (!SHA.test(sha) || !/^[a-zA-Z0-9_./-]+$/.test(path) ||
      path.startsWith('/') || path.includes('..')) throw Error('Unsafe pinned evidence path');
  return RAW + '/' + sha + '/' + path;
};
const link = (sha, path, label) =>
  '<a href="' + esc('https://github.com/' + REPO + '/blob/' + sha + '/' + path) +
  '" target="_blank" rel="noopener noreferrer">' + esc(label) + ' ↗</a>';
const pct = n => (Number.isFinite(n) ? (100*n).toFixed(1)+'%' : 'Not reported');
const decimal = n => (Number.isFinite(n) ? (100*n).toFixed(2)+'%' : 'Not measured');
function reportParity(report, expectedSize, requireSelection = true) {
  if (!report || report.input?.sha256 !== INPUT_SHA ||
      report.input?.question_count !== expectedSize ||
      (requireSelection && report.input?.selection?.question_ids_sha256 !== SELECTION_SHA) ||
      !report.planes || typeof report.planes !== 'object') {
    throw Error('Report input/selection identity differs from frozen cohort');
  }
  return report;
}
function scoreFor(report, plane, backend, metric) {
  const result = report?.planes?.[plane]?.backends?.[backend];
  const data = result?.aggregate;
  if (!data || result?.failures?.runtime_failure_count !== 0 ||
      result?.failures?.ingestion_failure_count !== 0 ||
      result?.failures?.out_of_corpus_returned_count !== 0 ||
      data.evaluated_question_count !== 43 ||
      data.excluded_abstention_count !== 3 ||
      data.excluded_no_user_target_count !== 4) return null;
  const score = data.headline?.[metric];
  return Number.isFinite(score) && score >= 0 && score <= 1 ? score : null;
}
function checkPartial(data, name) {
  if (data == null) return null; // turn-plane may not have been executed
  const completed = data.question_count_completed;
  const planned = data.question_count_preregistered;
  const scored = data.aggregate?.evaluated_question_count;
  const missing = data.missing_question_ids;
  const failures = data.failures || {};
  if (!Number.isInteger(completed) || !Number.isInteger(planned) ||
      planned !== 50 || completed < 0 || completed > 50 ||
      !Number.isInteger(scored) || scored < 0 || scored > completed ||
      !Array.isArray(missing) || missing.length !== planned - completed ||
      !['runtime_failure_count','ingestion_failure_count','out_of_corpus_returned_count']
        .every(k=>failures[k] === 0)) {
    throw Error('Incomplete or failed '+name+' execution; decline numeric projection');
  }
  return {completed,planned,scored,errors:0};
}
function parseCSV(raw) {
  if (typeof raw !== 'string' || raw.length > 1000000) throw Error('Invalid AMB raw CSV');
  const rows=[], fields=[];
  let quote=false, current='';
  for (let i=0;i<raw.length;i++) {
    const c=raw[i];
    if (c==='"') {if (quote && raw[i+1]==='"') {current+='"';i++;} else quote=!quote;}
    else if (c===',' && !quote) {fields.push(current);current='';}
    else if ((c==='\n' || c==='\r') && !quote) {
      if (c==='\r' && raw[i+1]==='\n') i++;
      fields.push(current); current='';
      if (fields.some(x=>x!=='') && fields.length > 1) rows.push(fields.splice(0));
      else fields.length=0;
    } else current+=c;
  }
  if (quote) throw Error('Unclosed CSV quote');
  if (current || fields.length) {fields.push(current);rows.push(fields);}
  const headers=rows.shift();
  if (!headers || new Set(headers).size!==headers.length ||
      !['query_id','category','pass_type','correct','judge_reason'].every(k=>headers.includes(k))) {
    throw Error('AMB case CSV schema mismatch');
  }
  if (rows.some(row=>row.length!==headers.length)) throw Error('AMB CSV record width mismatch');
  const objects=rows.map(row=>Object.fromEntries(headers.map((h,i)=>[h,row[i]])));
  const ids=new Set(objects.map(x=>x.query_id));
  if (ids.size!==objects.length) throw Error('AMB case IDs repeated');
  if (objects.some(x=>!['True','False'].includes(x.correct))) throw Error('AMB verdict missing');
  return {total:objects.length,correct:objects.filter(x=>x.correct==='True').length,
    excessFailures:objects.filter(x=>x.correct==='False' &&
      x.judge_reason.includes('unexpected belief in relevantBeliefs')).length,
    failed:objects.filter(x=>x.correct==='False').length};
}
function candidatesMarkup(rows, sha) {
  const head = '<thead><tr><th>Runtime / configuration</th><th>Session recall all @5</th>'+
    '<th>Turn recall all @10</th><th>Execution coverage</th><th>Raw evidence</th></tr></thead>';
  const cell = n => n == null ? '<span class="live-unknown">Not yet reportable</span>'
                           : '<strong class="live-number">'+decimal(n)+'</strong>';
  const body = rows.map(r=>'<tr><th scope="row">'+esc(r.name)+'</th><td>'+cell(r.session)+
    '</td><td>'+cell(r.turn)+'</td><td>'+esc(r.coverage)+'</td><td>'+
    (r.path ? link(sha,r.path,'View report') : esc('Not available'))+'</td></tr>').join('');
  return '<table class="live-table">'+head+'<tbody>'+body+'</tbody></table>';
}
function getRef(branch) {
  const encoded = branch.split('/').map(encodeURIComponent).join('/');
  return fetch(API+'/git/ref/heads/'+encoded, {cache:'no-store',headers:{Accept:'application/vnd.github+json'}})
    .then(resp=>{if (!resp.ok) throw Error('GitHub ref status '+resp.status);return resp.json();})
    .then(x=>{const sha=x?.object?.sha;if(!SHA.test(sha))throw Error('Invalid public branch SHA');return sha;});
}
async function getPinned(sha,path,optional=false) {
  const resp=await fetch(makeUrl(sha,path), {cache:'no-store'});
  if (resp.status===404 && optional) return null;
  if (!resp.ok) throw Error(path.split('/').pop()+': HTTP '+resp.status);
  if (path.endsWith('.json.gz')) {
    if (typeof DecompressionStream==='undefined' || !resp.body) {
      throw Error('Browser lacks gzip stream support');
    }
    return new Response(resp.body.pipeThrough(new DecompressionStream('gzip'))).json();
  }
  if (path.endsWith('.json')) return resp.json();
  return resp.text();
}
const readMaybe = async (sha,path) => {
  try {return await getPinned(sha,path,true);} catch (error) {
    return {__fetchError:error.message};
  }
};
function shorten(sha) {return sha.slice(0,12);}
function sourceLine(branch,sha) {
  return '<span>Source branch: <code>'+esc(branch)+'</code></span> · '+
   '<a target="_blank" rel="noopener noreferrer" href="'+esc('https://github.com/'+REPO+'/commit/'+sha)+'">'+shorten(sha)+' ↗</a>';
}
async function competitorView() {
  const node=document.getElementById('liveCompetitorRows');
  const status=document.getElementById('liveCompetitorStatus');
  if (!node || !status) return;
  const sha=await getRef(COMP_BRANCH);
  const paths={
    hindsight:ROOT+'640-hindsight/subset50/hindsight-50.json',
    mem0:ROOT+'mem0/subset50/mem0-50.json.gz',
    control:ROOT+'controls/subset50/controls-50.json.gz',
    cogneeSession:ROOT+'811-cognee/subset50/session.cognee_gliner_local.summary.json',
    cogneeTurn:ROOT+'811-cognee/subset50/turn.cognee_gliner_local.summary.json',
    jevSession:ROOT+'817-jev-mem/subset50/session.jev_mem_laya.summary.json',
    jevTurn:ROOT+'817-jev-mem/subset50/turn.jev_mem_laya.summary.json'
  };
  const entries=await Promise.all(Object.entries(paths).map(async ([id,path])=>[id,await readMaybe(sha,path)]));
  const data=Object.fromEntries(entries);
  const rows=[];
  const failures=[];
  for (const [id,name,backend] of [
    ['hindsight','Hindsight 0.10.2 · local chunks + ONNX','hindsight_chunks_onnx'],
    ['mem0','Mem0 OSS 2.2.1 · explicit memory','mem0_explicit'],
    ['control','Agent Memory · frozen control','agent_memory']]) {
    const doc=data[id];
    const path=paths[id];
    try {
      if (!doc || doc.__fetchError) throw Error(doc?.__fetchError||'Unavailable');
      reportParity(doc,50);
      const session=scoreFor(doc,'session',backend,'recall_all@5');
      const turn=scoreFor(doc,'turn',backend,'recall_all@10');
      if (session===null || turn===null) throw Error('Score population or failure audit mismatch');
      rows.push({name,session,turn,coverage:'50/50 attempted; 43 scored per plane · candidate',path});
    } catch(error) {
      rows.push({name,session:null,turn:null,coverage:'Evidence pending verification',path});
      failures.push(name+': '+error.message);
    }
  }
  for (const [id,name,short] of [
    ['cognee','Cognee 1.6.4 · local GLiNER','Cognee'],
    ['jev','Jev-Mem · local Laya','Jev-Mem']]) {
    const first=short==='Cognee'?'cognee':'jev';
    const sp=paths[first+'Session'],tp=paths[first+'Turn'];
    try {
      const s=checkPartial(data[first+'Session'],short+' session');
      const t=checkPartial(data[first+'Turn'],short+' turn');
      if (data[first+'Session']?.__fetchError || data[first+'Turn']?.__fetchError)
        throw Error(data[first+'Session']?.__fetchError || data[first+'Turn']?.__fetchError);
      rows.push({name,session:null,turn:null,coverage:
        'Session '+(s?s.completed+'/50':'not started')+
        ' · turn '+(t?t.completed+'/50':'not started')+
        ' · partial, no aggregate score',path:sp});
    } catch(error) {
      rows.push({name,session:null,turn:null,coverage:'Partial source requires verification',path:sp});
      failures.push(short+': '+error.message);
    }
  }
  node.innerHTML=candidatesMarkup(rows,sha);
  status.innerHTML=sourceLine(COMP_BRANCH,sha) + 
   '<span class="live-updated"> · Checked '+esc(new Date().toLocaleTimeString())+'</span>';
  const notice=document.getElementById('liveCompetitorNotice');
  if(notice) notice.textContent=failures.length
    ? 'Some source files could not be validated ('+failures.length+'); scores are withheld for those rows.'
    : 'Complete 50-question candidate comparisons shown; partial runs show coverage only.';
}
async function externalView() {
  const node=document.getElementById('liveExternalResults');
  const status=document.getElementById('liveExternalStatus');
  if (!node || !status) return;
  const sha=await getRef(EXTERNAL_BRANCH);
  const paths={
    am:AMB+'case-outcomes-agent-memory.csv',
    bm25:AMB+'case-outcomes-bm25.csv',
    arenaAM:MEMORYARENA+'agent_memory/all_results.json',
    arenaNone:MEMORYARENA+'none/all_results.json',
    arenaLong:MEMORYARENA+'long_context_qwen2.5-3b-instruct-q4_k_m/all_results.json'
  };
  const d=Object.fromEntries(await Promise.all(Object.entries(paths)
    .map(async([key,path])=>[key,await readMaybe(sha,path)])));
  let am=null,bm=null;
  try {
    if(typeof d.am==='string' && typeof d.bm25==='string') {
      am=parseCSV(d.am);bm=parseCSV(d.bm25);
      if(am.total!==77 || bm.total!==77 || am.correct!==15 || bm.correct!==8 ||
         am.excessFailures!==60 || am.failed!==62) {
        throw Error('Unexpected full-split execution revision; needs renewed review');
      }
    }
  } catch(e) {am=null;bm=null;}
  const amb=am&&bm
    ? '<div class="live-metric-row"><div><span>Agent Memory</span><strong>'+am.correct+
       ' / '+am.total+'</strong><small>'+pct(am.correct/am.total)+' strict success</small></div>'+
      '<div><span>BM25 · same native run</span><strong>'+bm.correct+' / '+bm.total+
      '</strong><small>'+pct(bm.correct/bm.total)+' strict success</small></div>'+
      '<div><span>False-positive retrieval failures</span><strong>'+am.excessFailures+
      ' / '+am.failed+'</strong><small>Unexpected memories in failed cases</small></div></div>'
    : '<p class="live-unknown">AMB candidate result is not verified or has changed. Consult its raw output.</p>';
  let arena=null;
  try {
    const named=[['No memory',d.arenaNone],['Long context',d.arenaLong],['Agent Memory',d.arenaAM]];
    if(named.every(([,x])=>x&&typeof x==='object'&&Number.isFinite(x.avg_progress_score)&&
       Number.isFinite(x.overall_average_passrate)&&x.avg_progress_score>=0&&x.avg_progress_score<=1&&
       x.overall_average_passrate>=0&&x.overall_average_passrate<=1)) {
      arena='<div class="live-arena-values">'+named.map(([n,x])=>
        '<span><strong>'+esc(n)+'</strong> · progress '+pct(x.avg_progress_score)+
        ' · task success '+pct(x.overall_average_passrate)+'</span>').join('')+'</div>';
    }
  }catch(e){arena=null;}
  node.innerHTML='<article class="live-external-card"><span class="live-card-label">Independent AMB harness · local candidate</span>'+
    '<h3>PrecisionMemBench · full single-turn split</h3>'+
    '<p>Retrieval only. Same original AMB dataset and scorer. No official upstream placement.</p>'+
    amb+'<p class="live-source-links">'+link(sha,paths.am,'Agent Memory case CSV')+' · '+
    link(sha,paths.bm25,'BM25 case CSV')+'</p>'+
    '<p class="live-caveat">Published Hindsight scores use LLM ingestion and structured retrieval filters. They are not a controlled one-variable comparison with this no-LLM, query-only run.</p></article>'+
    '<article class="live-external-card"><span class="live-card-label">MemoryArena · one exploratory task</span>'+
    '<h3>Multi-session physics · task 19</h3>'+
    '<p>One task, local Qwen2.5-3B agent and judge. Not a research leaderboard result.</p>'+
    (arena || '<p class="live-unknown">Experiment result unavailable or unverified.</p>')+
    '<p class="live-source-links">'+link(sha,paths.arenaAM,'Native Agent Memory result')+'</p>'+
    '<p class="live-caveat">The weak judge and one-task sample cannot support a product-wide inference.</p></article>';
  status.innerHTML=sourceLine(EXTERNAL_BRANCH,sha)+
    '<span class="live-updated"> · Checked '+esc(new Date().toLocaleTimeString())+'</span>';
}
let running=false;
async function refresh(){
  if(running)return;
  running=true;
  const button=document.getElementById('liveRefresh');
  if(button){button.disabled=true;button.textContent='Checking GitHub…';}
  const [c,e]=await Promise.allSettled([competitorView(),externalView()]);
  for(const [result,elem] of [[c,'liveCompetitorStatus'],[e,'liveExternalStatus']]) {
    if(result.status==='rejected') {
      const node=document.getElementById(elem);
      if(node)node.textContent='Live source temporarily unavailable: '+result.reason.message+
        '. Existing qualified leaderboard above remains unchanged.';
      const slot=document.getElementById(elem==='liveCompetitorStatus' ? 'liveCompetitorRows' : 'liveExternalResults');
      if(slot)slot.innerHTML='<p class="live-loading">Latest candidate evidence unavailable. '+
        'Use the source-branch links and try again later. No benchmark scores were inferred.</p>';
    }
  }
  if(button){button.disabled=false;button.textContent='Check for new evidence ↻';}
  running=false;
}
root.AgentMemoryLiveEvidence={reportParity,scoreFor,checkPartial,parseCSV,makeUrl,refresh};
if(typeof module!=='undefined' && module.exports)module.exports=root.AgentMemoryLiveEvidence;
if(typeof document!=='undefined') {
  const go=()=>{document.getElementById('liveRefresh')?.addEventListener('click',refresh);refresh();
    setInterval(()=>{if(document.visibilityState==='visible')refresh();},15*60*1000);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',go,{once:true});
  else go();
}
})(typeof window!=='undefined'?window:globalThis);
