"""Compatibility alias -- this module lives at ``agentmem_ref.memory.failure_memory``."""
import sys
from .memory import failure_memory as _real
sys.modules[__name__] = _real
