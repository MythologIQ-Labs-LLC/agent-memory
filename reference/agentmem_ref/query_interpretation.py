"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.query_interpretation``."""
import sys
from .runtime import query_interpretation as _real
sys.modules[__name__] = _real
