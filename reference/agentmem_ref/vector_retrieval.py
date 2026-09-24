"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.vector_retrieval``."""
import sys
from .runtime import vector_retrieval as _real
sys.modules[__name__] = _real
