"""Paired synthetic development evidence, no independent or accepted-lane claim."""
import importlib.util,json,platform,subprocess,sys,tempfile,time
from pathlib import Path
runtime,harness,output=map(Path,sys.argv[1:4]);size=int(sys.argv[4])
sys.path.insert(0,str(runtime/'reference'))
spec=importlib.util.spec_from_file_location('scale_experiment',harness/'tools/jarvis_scale/experiment.py');ex=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ex;spec.loader.exec_module(ex)
records,cases=ex.workload(size,825);results=[]
start=time.perf_counter();index=ex.IndexedArm(records);index_ms=(time.perf_counter()-start)*1000
try:r=ex.evaluate(index,cases,5,3);r['ingest_ms']=index_ms;results.append(r)
finally:index.close()
with tempfile.TemporaryDirectory(prefix='context-profile-scale-') as tmp:
 start=time.perf_counter();native=ex.AgentMemoryArm(records,Path(tmp));ingest_ms=(time.perf_counter()-start)*1000
 try:
  for profile in ('all_returned','lexical_content'):
   class ProfileArm:
    name='agent_memory_context_'+profile
    def recall(self,query,scope,limit):
     if scope not in native.handles:native.handles[scope]=native._open(scope)
     p=native.handles[scope].recall_context(query,consumer_profile=profile,max_items=limit,
       max_chars_per_item=20000,max_total_chars=1000000)
     return [native.mapping[i['fact_ref']] for i in p['items'] if i['state'] in ('resolved','truncated')]
   r=ex.evaluate(ProfileArm(),cases,5,3);r['shared_ingest_ms']=ingest_ms;results.append(r)
 finally:native.close()
p={'evidence_class':'synthetic_development_only_not_independent','runtime_sha':subprocess.check_output(['git','-C',str(runtime),'rev-parse','HEAD'],text=True).strip(),'harness_sha':subprocess.check_output(['git','-C',str(harness),'rev-parse','HEAD'],text=True).strip(),'corpus_sha256':ex.digest(records,cases),'synthetic_episodes':size,'records':len(records),'cases':len(cases),'budget':5,'repeats':3,'results':results,'limitations':['shared runtime ingest across two profiles','fixed arm order','concurrent unrelated local test work; latency indicative only','no RSS/CPU/disk accounting','source/trust/temporal metadata parity remains unqualified','not an independent holdout; no real Jarvis access']}
output.write_text(json.dumps(p,indent=2)+'\n')
for r in results:print({k:v for k,v in r.items() if k not in ('cases','by_family')})
