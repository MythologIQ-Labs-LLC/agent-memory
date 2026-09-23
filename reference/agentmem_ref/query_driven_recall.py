"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.query_driven_recall``."""
import sys
from .runtime import query_driven_recall as _real
sys.modules[__name__] = _real
