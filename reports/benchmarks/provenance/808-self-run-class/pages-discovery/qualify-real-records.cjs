'use strict';
/* Drive a run-discovery.js build end to end over REAL evidence bytes, offline.
 * Usage: node qualify-real-records.cjs <run-discovery.js> <evidence checkout> <817 manifest list file>
 * Two simulated sources: the 12 manifests that claude/817-jev-mem-execution-no-ci serves under
 * reports/benchmarks/runs/ (byte-identical to the audited originals), and the self-run records
 * under reports/benchmarks/self-run-candidates/. GitHub API responses are mocked from local files;
 * report bytes are hashed with the real WebCrypto and gzip is inflated with DecompressionStream.
 */
const fs=require('node:fs'),path=require('node:path');
const [appPath,root,listFile,mode='both']=process.argv.slice(2);
const legacy=fs.readFileSync(listFile,'utf8').trim().split('\n');
const walk=d=>fs.readdirSync(path.join(root,d),{withFileTypes:true}).flatMap(e=>
  e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);
const selfRun=walk('reports/benchmarks/self-run-candidates').filter(p=>p.endsWith('.json'));
const raw=new Set();
for(const p of (mode==='legacy-only'?legacy:[...legacy,...selfRun])){const m=JSON.parse(fs.readFileSync(path.join(root,p)));raw.add(m.normalized_run.uri);}
const branches={
 'claude/817-jev-mem-execution-no-ci':{sha:'1'.repeat(40),prefix:'reports/benchmarks/runs/',files:[...legacy,...raw]},
 'claude/810-external-exec-no-ci':{sha:'2'.repeat(40),prefix:'reports/benchmarks/self-run-candidates/',files:[...selfRun,...raw]},
};
if(mode==='legacy-only')delete branches['claude/810-external-exec-no-ci'];
const settings={schema_version:1,kind:'public-candidate-manifest-sources',authority_effect:'none',
 repository:'MythologIQ-Labs-LLC/agent-memory',read_only:true,
 sources:Object.entries(branches).map(([branch,b])=>({branch,prefix:b.prefix,max_manifest_files:48,max_partial_files:24}))};
const nodes=Object.fromEntries(['discoveredRunRows','discoveredRunStatus','discoveredRunProblems'].map(id=>[id,{innerHTML:'',textContent:''}]));
globalThis.window={dispatchEvent(){}};globalThis.CustomEvent=class{constructor(t,o){this.type=t;this.detail=o.detail}};
globalThis.document={getElementById:id=>nodes[id],readyState:'loading',addEventListener(){}};
const bySha=Object.fromEntries(Object.values(branches).map(b=>[b.sha,b]));
globalThis.fetch=async url=>{
 const u=String(url);
 if(u==='./data/live-sources.json')return{ok:true,json:async()=>settings};
 for(const [name,b] of Object.entries(branches)){
  if(u.endsWith('/git/ref/heads/'+name.split('/').map(encodeURIComponent).join('/')))return{ok:true,json:async()=>({object:{sha:b.sha}})};
 }
 if(u.includes('/git/commits/'))return{ok:true,json:async()=>({tree:{sha:u.split('/').at(-1)}})};
 if(u.includes('/git/trees/')){
  const b=bySha[u.split('/git/trees/')[1].split('?')[0]];
  return{ok:true,json:async()=>({truncated:false,tree:b.files.map(p=>({type:'blob',path:p,size:fs.statSync(path.join(root,p)).size}))})};
 }
 const m=/raw\.githubusercontent\.com\/[^/]+\/[^/]+\/([0-9a-f]{40})\/(.+)$/.exec(u);
 if(m){const bytes=fs.readFileSync(path.join(root,m[2]));
  return{ok:true,json:async()=>JSON.parse(bytes),arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};}
 throw Error('unexpected '+u);
};
const app=require(path.resolve(appPath));
const verdicts={};
for(const [name,b] of Object.entries(branches))for(const p of b.files.filter(f=>f.startsWith(b.prefix)&&f.endsWith('manifest.json'))){
 try{app.validateManifest(JSON.parse(fs.readFileSync(path.join(root,p))),p);verdicts[p]='valid';}
 catch(e){verdicts[p]='refused: '+e.message;}
}
(async()=>{
 await app.refresh(true);
 const rows=app.getLastRows();
 const out={rows:rows.map(r=>({manifest:r.manifestPath,review:r.review,score:r.score,coverage:r.coverage})),
   verdicts,status:nodes.discoveredRunStatus.textContent,problems:nodes.discoveredRunProblems.textContent};
 console.log(JSON.stringify(out,null,1));
})().catch(e=>{console.error(e);process.exitCode=1;});
