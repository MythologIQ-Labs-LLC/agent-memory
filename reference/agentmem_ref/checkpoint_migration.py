"""Compatibility alias -- this module lives at ``agentmem_ref.memory.checkpoint_migration``."""
import sys
from .memory import checkpoint_migration as _real
sys.modules[__name__] = _real
