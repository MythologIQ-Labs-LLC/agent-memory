import sys, json, tempfile
from pathlib import Path
ROOT=Path(sys.argv[1]); sys.path.insert(0,str(ROOT/"reference"))
import agentmem_ref, agentmem_ref.runtime_composition as _rc
assert str(Path(_rc.__file__).resolve()).startswith(str(ROOT.resolve())), _rc.__file__
sys.path.insert(0,"/tmp/claude-0/wt3/eval/scripts")
import run_served_memory_lifecycle_scenarios as L
assert str(Path(sys.modules["agentmem_ref.runtime_composition"].__file__).resolve()).startswith(str(ROOT.resolve()))
from agentmem_ref.adapter import RecallContext
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
from agentmem_ref.runtime_config import validate_runtime_configuration
def build(events, tmp):
    data={"schema":L.SCHEMA,"tenant":"t","project":"p","purpose":"probe","events":events,"queries":[{"id":"q","query":"x","intent":"current","budget":1}]}
    L.validate_inputs(data)
    corpora=L._host_corpora(data); reg=L._host_registry(corpora)
    rt=ConfiguredCompositionRuntime.create(Path(tmp),tenant="t",verifier_registry=reg,plan=validate_runtime_configuration(json.loads(L.CONFIG.read_text())))
    labels={}
    for e in events:
        if e["op"]=="retain":
            o=rt.retain(L._event_proposal(data,e,{"tenant":"t","project":"p"},op="retain"),e["text"],temporal=e.get("temporal"))
        else:
            ev=corpora[e["id"]].evidence_for(target_reference=L._memory_ref(e["memory"]),criterion="value-correction",pre_state=prev[e["memory"]],proposed_value=e["text"])
            o=rt.correct(L._event_proposal(data,e,{"tenant":"t","project":"p"},op=e["op"],version=1),e["text"],evidence=ev,temporal=e.get("temporal"),replacement_kind="state_change" if e["op"]=="update" else "error_correction")
        assert o.committed,(e,o)
        labels[o.fact_uuid]=e["id"]; prev[e["memory"]]=e["text"]
    return rt,labels
prev={}
CTX=RecallContext(target_domain_refs=("t","p"),principal_ref="agent:quality-evaluation",project_ref="p",purpose="probe")
