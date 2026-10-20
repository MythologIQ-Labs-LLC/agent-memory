"""Diagnostic native AMB scoring of public context profiles, never accepted lane evidence."""
import copy, hashlib, json, os, platform, statistics, subprocess, sys, tempfile, time, types
from pathlib import Path
workspace, runtime, output = map(Path, sys.argv[1:4])
for name, path in [('memory_bench', workspace/'amb/src/memory_bench'),('memory_bench.dataset',workspace/'amb/src/memory_bench/dataset')]:
    module=types.ModuleType(name); module.__path__=[str(path)]; sys.modules[name]=module
sys.path.insert(0,str(runtime/'reference'))
os.environ['PRECISIONMEMBENCH_DATA_PATH']=str(workspace/'precisionmembench/fixtures')
for key in list(os.environ):
    if key.startswith(('AMB_','OMB_','AGENT_MEMORY_AMB_')): os.environ.pop(key)
from agentmem_ref import AgentMemory
from amb_agent_memory_bridge import _scope, _logical_id, _TENANT, _ACTOR, _PURPOSE
from memory_bench.dataset.precisionmembench import PrecisionMemBenchDataset
D=PrecisionMemBenchDataset(); mapping={}; rows=[]
with tempfile.TemporaryDirectory(prefix='context-profile-replay-') as tmp:
    documents=D.load_documents('single-turn')
    for user in sorted({d.user_id for d in documents}):
        with AgentMemory.open(tmp,tenant=_TENANT,actor_id=_ACTOR,scope=_scope(user),purpose=_PURPOSE) as m:
            for d in documents:
                if d.user_id != user: continue
                r=m.remember(_logical_id(d.id,d.user_id),d.content,observed_at=d.timestamp)
                assert r['committed'];mapping[r['fact_uuid']]=d
    for i,q in enumerate(D.load_queries('single-turn')):
        arms={}; k=q.meta['retrieval_limit']
        with AgentMemory.open(tmp,tenant=_TENANT,actor_id=_ACTOR,scope=_scope(q.user_id),purpose=_PURPOSE) as m:
            original=m.recall(q.query,budget=k) if q.query.strip() and k>0 else {}
            profiles=['all_returned','lexical_content'] if i%2==0 else ['lexical_content','all_returned']
            for profile in profiles:
                start=time.perf_counter()
                package=m.recall_context(q.query,max_items=k,consumer_profile=profile,
                    max_chars_per_item=20000,max_total_chars=1000000) if q.query.strip() and k>0 else None
                elapsed=(time.perf_counter()-start)*1000
                refs=[x['fact_ref'] for x in package['items'] if x['state'] in ('resolved','truncated')] if package else []
                if package: assert package['recall']['returned']==original['returned']
                scored=copy.deepcopy(q); correct,reason=D.score_retrieval(scored,[mapping[x] for x in refs])
                arms[profile]={'correct':correct,'reason':reason,'meta':scored.meta,'returned_ids':[mapping[x].id for x in refs],
                    'elapsed_ms':elapsed,'package':package}
            after=m.recall(q.query,budget=k) if q.query.strip() and k>0 else {}
            for key in ('candidates','admitted','returned','return_policy'):assert original.get(key)==after.get(key)
        rows.append({'case_id':q.id,'category':q.meta['category'],'query':q.query,'raw_returned_ids':[mapping[x].id for x in original.get('returned',[])],'arms':arms})
        output.write_text(json.dumps({'rows':rows}))  # reproducible checkpoint, not an acceptance claim
summary={}
for profile in ('all_returned','lexical_content'):
    rr=[r['arms'][profile] for r in rows]; precisions=[x['meta']['retrieval_precision'] for x in rr if x['meta']['retrieval_precision'] is not None];recalls=[x['meta']['retrieval_recall'] for x in rr if x['meta']['retrieval_recall'] is not None]
    no_answer=[x for x in rr if x['meta']['pass_type']=='trivially-empty']
    summary[profile]={'strict':sum(x['correct'] for x in rr),'cases':len(rr),'metrics':D.summary_metrics(rr),'precision_denominator':len(precisions),'recall_denominator':len(recalls),'returned_count':sum(len(x['returned_ids']) for x in rr),'must_exclude_failure_cases':sum(any('forbidden belief' in f for f in x['meta']['failures']) for x in rr),'correct_empty_diagnostic':sum(not x['meta']['relevant_beliefs'] for x in no_answer),'empty_diagnostic_cases':len(no_answer),'p50_ms':statistics.median(x['elapsed_ms'] for x in rr)}
report={'kind':'known_AMB_diagnostic_native_scorer_public_context_profiles_not_full_CLI','runtime_sha':subprocess.check_output(['git','-C',str(runtime),'rev-parse','HEAD'],text=True).strip(),'base_sha':'585e76fb87e5c08da51020327a70d6d1807e06b4','amb_sha':subprocess.check_output(['git','-C',str(workspace/'amb'),'rev-parse','HEAD'],text=True).strip(),'fixture_sha':subprocess.check_output(['git','-C',str(workspace/'precisionmembench'),'rev-parse','HEAD'],text=True).strip(),'python':sys.version,'platform':platform.platform(),'summary':summary,'rows':rows}
output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n'); print(json.dumps(summary,indent=2))
