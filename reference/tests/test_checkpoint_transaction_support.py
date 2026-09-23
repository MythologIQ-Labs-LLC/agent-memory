"""Issue #419: keep migration behind the public checkpoint transaction seam."""

from __future__ import annotations

import inspect
import unittest

from agentmem_ref.memory import checkpoint_migration
from agentmem_ref.runtime.checkpoint_transactions import (
    CheckpointTransactionSession,
    CheckpointTransactionSupport,
    CommittedCheckpointBundle,
)


class CheckpointTransactionSupportTests(unittest.TestCase):
    def test_migration_does_not_reach_into_restart_runtime_private_transaction_helpers(self):
        source = inspect.getsource(checkpoint_migration)
        forbidden = (
            "_assert_manifest_matches_journal",
            "_exclusive_checkpoint_lock",
            "_read_generation_journal",
            "_validate_generation_journal",
            "_snapshot_governance",
            "_snapshot_substrate",
            "_restore_adapter",
            "_restore_substrate",
            "._current_manifest_and_journal",
            "._observed_generation",
            "._observed_manifest_digest",
            ".lock_path",
            ".journal_path",
            ".manifest_path",
            ".substrate_path",
            ".governance_path",
        )
        for token in forbidden:
            self.assertNotIn(token, source, token)

    def test_public_seam_types_are_explicit(self):
        self.assertFalse(CheckpointTransactionSupport.__name__.startswith("_"))
        self.assertFalse(CheckpointTransactionSession.__name__.startswith("_"))
        self.assertFalse(CommittedCheckpointBundle.__name__.startswith("_"))


if __name__ == "__main__":
    unittest.main()
