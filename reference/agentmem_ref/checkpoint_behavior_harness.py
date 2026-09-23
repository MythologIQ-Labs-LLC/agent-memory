"""Compatibility alias -- this module lives at ``agentmem_ref.harness.checkpoint_behavior_harness``."""
import sys
from .harness import checkpoint_behavior_harness as _real
sys.modules[__name__] = _real
