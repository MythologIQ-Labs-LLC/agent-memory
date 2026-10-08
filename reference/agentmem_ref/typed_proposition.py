"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.typed_proposition``."""
import sys
from .runtime import typed_proposition as _real
sys.modules[__name__] = _real
