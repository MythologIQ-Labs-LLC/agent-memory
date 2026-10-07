"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.representation_cache``."""
import sys
from .runtime import representation_cache as _real
sys.modules[__name__] = _real
