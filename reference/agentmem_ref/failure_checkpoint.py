"""Compatibility alias -- this module lives at ``agentmem_ref.memory.failure_checkpoint``."""
import sys
from .memory import failure_checkpoint as _real
sys.modules[__name__] = _real
