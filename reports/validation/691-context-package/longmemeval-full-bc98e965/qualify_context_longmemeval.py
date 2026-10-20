"""Full pinned LME, paired public profiles. No scorer/runtime/fixture edits.

Raw control invokes the existing _agent_memory adapter. Context profiles are an adapted
protocol, scored separately with the existing score_record/summarize functions. No gold
enters the runtime: the subclass sees only the original positional target, text and query.
"""
import argparse, copy, hashlib, json, os, platform, resource, subprocess, sys, time
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--runtime',type=Path,required=True);P.add_argument('--input',type=Path,required=True);P.add_argument('--plane',choices=['session','turn'],required=True);P.add_argument('--out',type=Path,required=True);P.add_argument('--max-questions',type=int);args=P.parse_args()
sys.path.insert(0,str(args.runtime/'reference'))
import run_longmemeval as lme
from agentmem_ref import AgentMemory as Native
DIGEST='d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442'
EXPECTED_SELECTION='7d738ae585fd4014c9d231088ff824864fded501adc07b0e08c2b97a28210c03'
ACTIVE_CAPTURE=[]
def usage():
 r=resource.getrusage(resource.RUSAGE_SELF);return {'user_s':r.ru_utime,'system_s':r.ru_stime,'rss_highwater_kib':r.ru_maxrss}
class CapturingMemory(Native):
 def remember(self,target,text,**kwargs):
  result=super().remember(target,text,**kwargs)
  if result.get('committed'):
   if not hasattr(self,'_eval_positions'):self._eval_positions={}
   self._eval_positions[result['fact_uuid']]=int(target.rsplit(':',1)[1])
  return result
 def recall(self,query,**kwargs):
  start=time.perf_counter();cpu=usage();raw=super().recall(query,**kwargs);now=usage()
  captures={'raw':{'wall_s':time.perf_counter()-start,'cpu_user_s':now['user_s']-cpu['user_s'],'cpu_system_s':now['system_s']-cpu['system_s']}}
  for profile in ('all_returned','lexical_content'):
   options=dict(kwargs);budget=options.pop('budget',50)
   start=time.perf_counter();cpu=usage()
   package=super().recall_context(query,consumer_profile=profile,max_items=budget,
       max_chars_per_item=10000000,max_total_chars=500000000,max_tokens=200000000,**options)
   now=usage();assert package['recall']['returned']==raw['returned']
   refs=[i['fact_ref'] for i in package['items'] if i['state'] in ('resolved','truncated')]
   assert all(i['state']=='resolved' for i in package['items']), 'Truncation/unresolved cannot be scored as complete delivered context'
   captures[profile]={'positions':[self._eval_positions[x] for x in refs], 'states':[i['state'] for i in package['items']],
       'selection':package.get('selection'),'budget':package['budget'],'wall_s':time.perf_counter()-start,
       'cpu_user_s':now['user_s']-cpu['user_s'],'cpu_system_s':now['system_s']-cpu['system_s']}
  after=super().recall(query,**kwargs)
  for key in ('candidates','admitted','returned','return_policy'):assert raw[key]==after[key],key
  ACTIVE_CAPTURE.append(captures)
  return raw
lme.AgentMemory=CapturingMemory
lme.configure_agent_memory(temporal_metadata='none',ranking_variant='default',budget=50,semantic_retrieval='off',recall_control='off')
start=time.perf_counter();before=usage();summaries,scan=lme._scan(args.input)
assert scan.hexdigest()==DIGEST;selected_ids=[str(x['question_id']) for x in summaries]
assert len(selected_ids)==500
assert hashlib.sha256('\n'.join(selected_ids).encode()).hexdigest()==EXPECTED_SELECTION
if args.max_questions:selected_ids=selected_ids[:args.max_questions]
rows={arm:[] for arm in ('raw','all_returned','lexical_content')};passes=[];failures=[]
args.out.mkdir(parents=True,exist_ok=True)
identity={'source_sha':subprocess.check_output(['git','-C',str(args.runtime),'rev-parse','HEAD'],text=True).strip(),
 'runtime_tree':subprocess.check_output(['git','-C',str(args.runtime),'rev-parse','HEAD:reference/agentmem_ref'],text=True).strip(),
 'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_sha256':DIGEST,
 'plane':args.plane,'source_questions':500,'selection_questions':len(selected_ids),'selection_id_sha256':hashlib.sha256('\n'.join(selected_ids).encode()).hexdigest(),
 'protocol':'raw uses frozen adapter semantics; public context profiles are separate adapted protocols; shared ingest and no generation/judging',
 'budgets':{'k':50,'max_chars_per_item':10000000,'max_total_chars':500000000,'max_tokens':200000000},
 'configuration':dict(lme._AGENT_MEMORY_CONFIGURATION),'python':sys.version,'platform':platform.platform(),
 'full_external_lane_qualification':False,'reason':'paired instrumentation; inherited candidate runtime, optional return protocol and locked environment require separate qualification',
 'hardware':{'cpu_count':os.cpu_count()},'started_epoch':time.time()}
(args.out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
for index,row in enumerate(lme._selected_questions(args.input,selected_ids,DIGEST,passes,args.plane)):
 items,_=lme.corpus(row,args.plane);ACTIVE_CAPTURE.clear();qstart=time.perf_counter()
 try:
  result=lme._agent_memory(str(row['question']),items,index,None)
  if result['ingestion_failures']:raise RuntimeError('ingestion failures')
  captured=ACTIVE_CAPTURE[0]
  for profile in rows:
   extra={'ingest_seconds':result['ingest_seconds'],'candidate_count':result['candidate_count'],'admitted_count':result['admitted_count']}
   if profile=='raw':ranked=result['ranked'];extra['resource']=captured['raw']
   else:
    detail=captured[profile];ranked=[items[pos]['id'] for pos in detail['positions']];extra['resource']={k:v for k,v in detail.items() if k not in ('positions','selection','states')};extra['selection']=detail['selection']
   scored=lme.score_record(row,args.plane,ranked,extra=extra);rows[profile].append(scored)
  if rows['raw'][-1]['ranked_top'] != rows['all_returned'][-1]['ranked_top']:raise RuntimeError('default package changes raw returned ranking')
 except Exception as exc:
  failures.append({'question_id':row['question_id'],'error':repr(exc)});raise
 finally:
  with (args.out/'checkpoint.jsonl').open('a') as out:
   out.write(json.dumps({'index':index,'question_id':row['question_id'],'items':len(items),'wall_s':time.perf_counter()-qstart,'completed':len(rows['raw']),'errors':failures[-1:] if failures else []})+'\n')
  (args.out/'rows.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
 if (index+1)%25==0:print(json.dumps({'completed':index+1,'plane':args.plane,'elapsed_s':round(time.perf_counter()-start,2)}),flush=True)
report={'identity':identity,'completed':len(rows['raw']),'summary':{profile:lme.summarize(value,args.plane) for profile,value in rows.items()},'passes':passes,'failures':failures,'wall_s':time.perf_counter()-start,'usage_before':before,'usage_after':usage(),'rows':rows}
(args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'completed':report['completed'],'wall_s':report['wall_s'],'headline':{p:r['aggregate']['headline'] for p,r in report['summary'].items()}},indent=2),flush=True)
