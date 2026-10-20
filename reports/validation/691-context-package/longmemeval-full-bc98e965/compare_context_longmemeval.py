import json,gzip,sys
from pathlib import Path
root=Path('/workspace/scratch/fa6d5f50ddfd/agent-memory-context-qualified')
out={}
for plane in ('session','turn'):
 p=Path('/tmp/691-lme-full-'+plane)
 if not (p/'report.json').exists():continue
 report=json.loads((p/'report.json').read_text());rows=report['rows'];raw=rows['raw'];chosen=rows['lexical_content']
 accepted_path=root/'reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v6'/('agent_memory-'+plane+'-24048d55e26d')/'report.rows.json.gz'
 accepted=json.loads(gzip.decompress(accepted_path.read_bytes()))[plane]['agent_memory'];old={r['question_id']:r for r in accepted}
 mismatches=[];regressions=[];gains=[];valid=0;delta={};totals={}
 for a,b in zip(raw,chosen):
  assert a['question_id']==b['question_id'];prior=old[a['question_id']]
  if a['ranked_top']!=prior['ranked_top'] or a['metrics']!=prior['metrics']:mismatches.append(a['question_id'])
  am=a.get('metrics',{}).get(plane,{});bm=b.get('metrics',{}).get(plane,{})
  if am and a['status']=='scored':
   valid+=1
   for k,v in am.items():
    if v is not None and bm.get(k) is not None:
     delta[k]=delta.get(k,0)+(bm[k]-v)
     if bm[k]<v:regressions.append({'question_id':a['question_id'],'metric':k,'before':v,'after':bm[k]})
     if bm[k]>v:gains.append({'question_id':a['question_id'],'metric':k,'before':v,'after':bm[k]})
 for arm, rr in rows.items():
  totals[arm]={'returned':sum(len(r['ranked_top']) for r in rr),'required_evidence_hits':sum(len(set(r['gold'])&set(r['ranked_top'])) for r in rr),'false_positive_ids':sum(len(set(r['ranked_top'])-set(r['gold'])) for r in rr),'recall_cpu_s':sum(r['resource']['cpu_user_s']+r['resource']['cpu_system_s'] for r in rr),'recall_wall_s':sum(r['resource']['wall_s'] for r in rr)}
 out[plane]={'completed':report['completed'],'scored':valid,'accepted_v6_rank_or_metric_mismatches':mismatches,'metric_mean_deltas':{k:v/valid for k,v in delta.items()},'metric_regressions':regressions,'metric_gains':gains,'totals':totals,'summary':report['summary'],'wall_s':report['wall_s'],'usage':report['usage_after']}
Path('/tmp/691-lme-full-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
for p,r in out.items():print(p,json.dumps({k:v for k,v in r.items() if k not in ('summary','metric_regressions','metric_gains')},indent=2));print('regression_questions',sorted(set(x['question_id'] for x in r['metric_regressions'])));print('gain_questions',len(set(x['question_id'] for x in r['metric_gains'])))
