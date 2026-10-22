"""#691 developer-preview gate: same-project content visibility != writer metadata authority.

Preregistered review-only regression tests. These intentionally fail against the
unmodified #691 candidate (base 585e76fb) pending an owner choice on the
public provenance policy. Do not weaken normal content admission to pass.
No accepted baseline, private data, frozen benchmark fixture or runtime change.
"""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory


TENANT = "tenant:691-provenance"
SCOPE = "project:691-provenance"
TARGET = "memory:writer-internal-reference"
TEXT = "The garden azaleas are purple."


def open_as(root: Path, actor: str) -> AgentMemory:
    return AgentMemory.open(
        root, tenant=TENANT, actor_id=actor, scope=SCOPE, purpose="691 provenance review"
    )


class CrossActorProvenanceReview(unittest.TestCase):
    def test_writer_still_receives_its_own_provenance(self):
        with tempfile.TemporaryDirectory(prefix="agent-memory-691-own-") as temp:
            memory = open_as(Path(temp), "agent:writer")
            try:
                outcome = memory.remember(TARGET, TEXT, source_ref="actor:writer-private")
                self.assertTrue(outcome["committed"], outcome)
                package = memory.recall_context("garden azaleas purple", max_items=3)
                matching = [item for item in package["items"] if item.get("content") == TEXT]
                self.assertEqual(len(matching), 1, package)
                self.assertEqual(matching[0]["provenance"]["memory_ref"], TARGET)
                self.assertEqual(matching[0]["provenance"]["source_ref"], "actor:writer-private")
            finally:
                memory.close()

    def test_other_project_member_may_read_content_but_not_writer_private_refs_by_default(self):
        with tempfile.TemporaryDirectory(prefix="agent-memory-691-cross-") as temp:
            root = Path(temp)
            writer = open_as(root, "agent:writer")
            try:
                outcome = writer.remember(TARGET, TEXT, source_ref="actor:writer-private")
                self.assertTrue(outcome["committed"], outcome)
            finally:
                writer.close()

            reader = open_as(root, "agent:reader")
            try:
                package = reader.recall_context("garden azaleas purple", max_items=3)
                matching = [item for item in package["items"] if item.get("content") == TEXT]
                # Positive control: this is not a cross-project admission rejection.
                self.assertEqual(len(matching), 1, package)
                item = matching[0]
                self.assertEqual(item["trust"], "untrusted_memory_text")
                self.assertEqual(item["authority_effect"], "none")
                prov = item["provenance"]
                self.assertEqual(prov["content_sha256"], hashlib.sha256(TEXT.encode()).hexdigest())
                # Separate text eligibility from authority to discover writer-declared
                # source refs or logical lineage identifiers. Missing and None are both
                # safe defaults, unless the owner explicitly authorizes sharing.
                self.assertFalse(prov.get("memory_ref"), prov)
                self.assertFalse(prov.get("source_ref"), prov)
                self.assertNotIn(TARGET, str(package))
                self.assertNotIn("actor:writer-private", str(package))
            finally:
                reader.close()


if __name__ == "__main__":
    unittest.main()
