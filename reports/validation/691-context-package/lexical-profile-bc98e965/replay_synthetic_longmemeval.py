"""Adapted diagnostic only: the existing synthetic LME scorer sees delivered context IDs."""
import importlib.util,json,sys
from pathlib import Path
runtime=Path(sys.argv[1]);profile=sys.argv[2];out=Path(sys.argv[3])
sys.path.insert(0,str(runtime/'reference'))
import run_longmemeval as lme
from agentmem_ref import AgentMemory as Native
class ContextMemory(Native):
    def recall(self,query,**kwargs):
        raw=super().recall(query,**kwargs)
        budget=kwargs.pop('budget',None)
        package=super().recall_context(query,consumer_profile=profile,max_items=budget or 100000,
                 max_chars_per_item=20000,max_total_chars=1000000,**kwargs)
        raw['returned']=[i['fact_ref'] for i in package['items'] if i['state'] in ('resolved','truncated')]
        raw['return_policy']={**package['recall']['return_policy'], 'evaluation_consumer_profile':profile,
                              'delivered_count':len(raw['returned']),'protocol':'adapted_synthetic_context_diagnostic'}
        return raw
lme.AgentMemory=ContextMemory
sys.argv=['run_longmemeval.py','--backend','agent_memory','--output',str(out)]
lme.main()
r=json.loads(out.read_text());r['diagnostic_protocol']='Public recall_context profile '+profile+'; synthetic fixture only; not accepted external LongMemEval lane or independent holdout';out.write_text(json.dumps(r,indent=2)+'\n')
