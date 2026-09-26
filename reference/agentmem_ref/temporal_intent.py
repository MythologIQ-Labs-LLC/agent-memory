"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.temporal_intent``."""
import sys
from .runtime import temporal_intent as _real
sys.modules[__name__] = _real
