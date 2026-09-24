"""Compatibility alias -- this module lives at ``agentmem_ref.memory.metabolism``."""
import sys
from .memory import metabolism as _real
sys.modules[__name__] = _real
