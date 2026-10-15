"""validation(#776 @ 5098577): deletion decisions are a pure function of governed state.

Property: for random interleavings of writes (with provenance to existing AND
not-yet-existing facts), state changes, governed deletions, re-creation of deleted
memory ids and recalls, every fact's deletion-family decision equals an independent
from-scratch oracle -- regardless of query order, warm caches, later writes, or
checkpoint recovery.
"""
from __future__ import annotations

import random
import unittest

from tests.test_776_adversarial_review import _Store
from tests.test_runtime_composition import _context

DELETION_FAMILY = {"tombstoned", "derived_from_tombstoned_source",
                   "logical_memory_deleted", "derived_from_deleted_logical_memory"}


def oracle(adapter):
    """Independent definition: a fact is deletion-refused iff it is in a deleted lineage
    or its provenance (episode_uuids, transitively over facts) reaches one."""
    deleted = set(adapter._tombstones)
    for key, record in adapter._tombstones.items():
        deleted.update(record.get("deleted_fact_uuids") or ())
    facts = {f.uuid: f for f in adapter._substrate.all_facts()}
    out = {}
    for uuid, fact in facts.items():
        if uuid in deleted:
            out[uuid] = True
            continue
        seen, stack, hit = set(), list(fact.episode_uuids), False
        while stack:
            ref = stack.pop()
            if ref in seen:
                continue
            seen.add(ref)
            if ref in deleted:
                hit = True
                break
            if ref in facts:
                stack.extend(facts[ref].episode_uuids)
        out[uuid] = hit
    return out


def observed(adapter, *, cold=False):
    if cold:
        adapter._deleted_lineage_cache = None
        adapter._derived_taint_memo = None
    ctx = _context()
    return {f.uuid: adapter._admission_refusal(f, ctx, "historical") in DELETION_FAMILY
            for f in adapter._substrate.all_facts()}


class DeletionDecisionProperties(unittest.TestCase):
    def run_seed(self, seed):
        rng = random.Random(seed)
        h = _Store(self)
        live, deleted, n = [], [], 0
        for step in range(28):
            op = rng.random()
            adapter = h.adapter
            known = [f.uuid for f in adapter._substrate.all_facts()]
            if op < 0.40 or not live:
                n += 1
                name = f"m{n}"
                refs = []
                if known and rng.random() < 0.7:
                    refs.append(rng.choice(known))
                if rng.random() < 0.35:  # forward citation of a fact id that may be written later
                    refs.append(f"ref-{rng.randint(1, 400):04d}")
                versions = [(f"{name} value {k} for seed {seed}", None if k == 0 else "state_change")
                            for k in range(rng.randint(1, 3))]
                h.chain(name, versions, evidence_refs=tuple(dict.fromkeys(refs)) or None)
                live.append(name)
            elif op < 0.60:
                name = live.pop(rng.randrange(len(live)))
                h.prune(name)
                deleted.append(name)
            elif op < 0.72 and deleted:
                name = deleted.pop(rng.randrange(len(deleted)))
                again = h.runtime.retain(h.proposal(name, 500 + step), f"{name} recreated at {step}")
                self.assertTrue(again.committed, again)
                live.append(name)
            else:
                h.recall(f"value seed {seed}")  # warms caches in arbitrary order
            warm, truth = observed(h.adapter), oracle(h.adapter)
            self.assertEqual(warm, truth, f"seed {seed} step {step}: warm cache diverged")
        self.assertEqual(observed(h.adapter, cold=True), oracle(h.adapter), f"seed {seed}: cold")
        h.runtime.durable_runtime.checkpoint()
        recovered = h.recovered().adapter
        self.assertEqual(observed(recovered), oracle(recovered), f"seed {seed}: after recovery")
        self.assertEqual(oracle(recovered), oracle(h.adapter), f"seed {seed}: recovery changed state")

    def test_random_interleavings(self):
        for seed in range(40):
            with self.subTest(seed=seed):
                self.run_seed(seed)


if __name__ == "__main__":
    unittest.main()
