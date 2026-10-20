"""#636 development-only real public semantic-off/on comparison.

No route monkeypatches, fabricated embeddings, internal substrate reads, API
changes, inference fees or answer judge. The fixture is known development input,
not a benchmark holdout. Off is still multi-route, never labelled lexical-only.
"""
from __future__ import annotations
import argparse
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import random
import resource
import subprocess
import tempfile
import time
from agentmem_ref import AgentMemory
from agentmem_ref.evaluation.route_attribution import attribute_returned_routes
from agentmem_ref.evaluation.paired_recall import CaseLabels, RunIdentity, compare_public_profiles


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def stable_recall(raw):
    """Fresh audit IDs/clocks are expected; preserve all retrieval semantics."""
    value = copy.deepcopy(raw)
    for receipt in value['admissions'].values():
        receipt.pop('decision_id', None)
        receipt.pop('evaluated_at', None)
    return value


def execute(root, fixture, mode, model_dir):
    context = fixture['context']
    options = dict(context, semantic_retrieval=mode, representation_dir=model_dir)
    cpu = resource.getrusage(resource.RUSAGE_SELF)
    start = time.perf_counter()
    with AgentMemory.open(root, **options) as memory:
        open_s = time.perf_counter() - start
        posture = memory.semantic_retrieval_posture()
        assert posture['status'] == ('disabled' if mode == 'off' else 'enabled')
        ids, texts = {}, {}
        start = time.perf_counter()
        for fact in fixture['facts']:
            receipt = memory.remember(fact['ref'], fact['text'])
            assert receipt['committed'], receipt
            ids[fact['ref']] = receipt['fact_uuid']
            texts[receipt['fact_uuid']] = fact['text']
        ingest_s = time.perf_counter() - start
        cases = []
        for case in fixture['cases']:
            observations, times = [], []
            for _ in range(fixture['repeats']):
                start = time.perf_counter()
                raw = memory.recall(case['query'], logical_memory_refs=case.get('logical_memory_refs', ()), budget=fixture['budget_k'])
                times.append(time.perf_counter() - start)
                observations.append(raw)
            assert all(stable_recall(raw) == stable_recall(x) for x in observations), 'nondeterministic retrieval semantics'
            required = frozenset(ids[x] for x in case['required'])
            forbidden = frozenset(ids[x] for x in case['forbidden'])
            route_report = attribute_returned_routes(raw, required_refs=required, forbidden_refs=forbidden)
            returned_texts = [texts[x] for x in raw['returned']]
            cases.append({'case_ref': case['ref'], 'raw': raw, 'repeat_receipts': observations, 'attribution': asdict(route_report),
                          'cold_first_recall_s': times[0], 'warm_recall_s': times[1:],
                          'context_chars': sum(map(len, returned_texts)),
                          'context_tokens_estimate_chars_div4': sum((len(t)+3)//4 for t in returned_texts)})
        # Real lifecycle and reopen controls, not synthetic label-based assertions.
        last = memory.remember('memory:lifecycle', 'Lifecycle diagnostic sentinel.')
        assert last['committed']
        deletion = memory.forget('memory:lifecycle', risk_class='low')
        assert deletion['committed'], deletion
        deleted = last['fact_uuid']
    with AgentMemory.open(root, **options) as memory:
        for case, before in zip(fixture['cases'], cases):
            after = memory.recall(case['query'], logical_memory_refs=case.get('logical_memory_refs', ()), budget=fixture['budget_k'])
            assert after['returned'] == before['raw']['returned'], 'reopen changed returned evidence'
        result = memory.recall('Lifecycle diagnostic sentinel', logical_memory_refs=('memory:lifecycle',))
        assert deleted not in result['admitted'] and deleted not in result['returned']
        foreign = memory.recall('deployment window', target_domain_refs=('tenant:other', 'project:other'), project_ref='project:other')
        assert not foreign['candidates'] and not foreign['returned']
        store = memory.verify_semantic_store() if mode == 'required' else None
    after_cpu = resource.getrusage(resource.RUSAGE_SELF)
    return {'mode': mode, 'posture': posture, 'ids': ids, 'cases': cases,
            'open_s': open_s, 'ingest_s': ingest_s,
            'cpu_user_s': after_cpu.ru_utime-cpu.ru_utime, 'cpu_system_s': after_cpu.ru_stime-cpu.ru_stime,
            'disk_bytes_after_close': sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
            'lifecycle': {'delete_reopen': True, 'recall_reopen': True, 'foreign_scope_empty': True},
            'semantic_store_verification': store}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture', type=Path, default=Path(__file__).parent/'fixtures/evaluation/636-supported-profiles-v1.json')
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    fixture = json.loads(args.fixture.read_text())
    root = Path(__file__).resolve().parents[1]
    source = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True))
    identity = {'source_sha': source, 'dirty': dirty, 'fixture_sha256': hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
                'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'platform': platform.platform(),
                'python': platform.python_version(), 'evidence_class': fixture['evidence_class']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix('.identity.json').write_text(json.dumps(identity, indent=2)+'\n')
    order = ['off', 'required']; random.Random(fixture['order_seed']).shuffle(order)
    arms = {}
    with tempfile.TemporaryDirectory(prefix='am-636-') as tmp:
        for mode in order:
            arms[mode] = execute(Path(tmp)/mode, fixture, mode, args.model_dir)
    assert arms['off']['ids'] == arms['required']['ids'], 'fact identity differs across arms'
    pairs = []
    ids = arms['off']['ids']
    for case, a, b in zip(fixture['cases'], arms['off']['cases'], arms['required']['cases']):
        common = dict(revision=source, corpus_digest=digest(fixture['facts']), questions_digest=digest(fixture['cases']),
                      labels_digest=digest([{k:c.get(k) for k in ('required','forbidden','no_safe_answer')} for c in fixture['cases']]),
                      harness_digest=identity['driver_sha256'], scope_digest=digest(fixture['context']),
                      case_ref=case['ref'], case_input_digest=digest({k:v for k,v in case.items() if k not in ('required','forbidden','no_safe_answer')}), budget_k=fixture['budget_k'])
        runs = [RunIdentity(profile_id=mode, configuration_digest=digest({'semantic_retrieval':mode,'posture':arms[mode]['posture']}), **common) for mode in ('off','required')]
        labels = CaseLabels(frozenset(ids[x] for x in case['required']), frozenset(ids[x] for x in case['forbidden']), case.get('no_safe_answer',False))
        result = compare_public_profiles(a['raw'], b['raw'], original_run=runs[0], candidate_run=runs[1], labels=labels)
        pairs.append({'case_ref':case['ref'], 'runs':[asdict(x) for x in runs], 'comparison':asdict(result)})
    report = {'identity': identity, 'arm_order': order, 'arms': arms, 'paired': pairs,
              'regression': any(x['comparison']['regression'] for x in pairs), 'unsupported':fixture['unsupported'],
              'limits':['one ingestion per arm; warm samples two per case', 'shared process highwater RSS cannot be attributed per arm', 'small author-visible cases; no independent task scorer or qualification', 'no pure single-route public configurations']}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'cases':len(pairs),'regression':report['regression']}))

if __name__ == '__main__':
    main()
