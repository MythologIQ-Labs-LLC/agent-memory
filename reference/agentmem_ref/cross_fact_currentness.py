"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.cross_fact_currentness``."""
import sys
from .runtime import cross_fact_currentness as _real
sys.modules[__name__] = _real
