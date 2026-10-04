"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.temporal_order_constraints``."""
import sys
from .runtime import temporal_order_constraints as _real
sys.modules[__name__] = _real
