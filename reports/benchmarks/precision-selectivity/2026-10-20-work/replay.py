import sys, types, json, hashlib, time, tempfile, os, subprocess
from pathlib import Path
ROOT=Path(sys.argv[1]).resolve()
RUNTIME=Path(sys.argv[2]).resolve()
OUTPUT=Path(sys.argv[3])
# Load the real AMB dataset/scorer without importing unrelated provider registries.
for name,path in [('memory_bench',ROOT/'amb/src/memory_bench'),('memory_bench.dataset',ROOT/'amb/src/memory_bench/dataset')]:
 m=types.ModuleType(name); m.__path__=[str(path)];sys.modules[name]=m
sys.path.insert(0,str(RUNTIME/'reference'))
os.environ['PRECISIONMEMBENCH_DATA_PATH']=str(ROOT/'precisionmembench/fixtures')
for key in list(os.environ):
 if key.startswith(('AMB_','OMB_','AGENT_MEMORY_AMB_')):os.environ.pop(key)
from memory_bench.dataset.precisionmembench import PrecisionMemBenchDataset
from memory_bench.models import Document
from agentmem_ref import AgentMemory
from amb_agent_memory_bridge import _scope, _logical_id, _TENANT, _ACTOR, _PURPOSE
D=PrecisionMemBenchDataset(); docs=D.load_documents('single-turn'); rows=[]; mapping={}
with tempfile.TemporaryDirectory(prefix='precision-diagnostic-819-') as tmp:
 for user in sorted({d.user_id for d in docs}):
  with AgentMemory.open(tmp,tenant=_TENANT,actor_id=_ACTOR,scope=_scope(user),purpose=_PURPOSE) as mem:
   for doc in docs:
    if doc.user_id!=user:continue
    r=mem.remember(_logical_id(doc.id,doc.user_id),doc.content,observed_at=doc.timestamp)
    assert r['committed'];mapping[r['fact_uuid']]=doc
 for q in D.load_queries('single-turn'):
  k=q.meta['retrieval_limit'];start=time.perf_counter();out={}
  if q.query.strip() and k>0:
   with AgentMemory.open(tmp,tenant=_TENANT,actor_id=_ACTOR,scope=_scope(q.user_id),purpose=_PURPOSE) as mem:
    out=mem.recall(q.query,budget=k)
  latency=(time.perf_counter()-start)*1000
  returned=[mapping[x] for x in out.get('returned',[])]; passed,reason=D.score_retrieval(q,returned)
  rows.append({'case_id':q.id,'query':q.query,'category':q.meta['category'],'correct':passed,'reason':reason,'meta':q.meta,'latency_open_and_recall_ms':latency,'returned_ids':[d.id for d in returned],'outcome':out,'fact_to_document':{x:mapping[x].id for x in out.get('candidates',[])}})
summary={'kind':'diagnostic-public-facade-replay-not-full-AMB-CLI','runtime_sha':subprocess.check_output(['git','-C',str(RUNTIME),'rev-parse','HEAD'],text=True).strip(),'amb_sha':subprocess.check_output(['git','-C',str(ROOT/'amb'),'rev-parse','HEAD'],text=True).strip(),'dataset_sha':subprocess.check_output(['git','-C',str(ROOT/'precisionmembench'),'rev-parse','HEAD'],text=True).strip(),'correct':sum(r['correct'] for r in rows),'total':len(rows),'metrics':D.summary_metrics(rows),'rows':rows}
OUTPUT.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print({k:v for k,v in summary.items() if k!='rows'})
