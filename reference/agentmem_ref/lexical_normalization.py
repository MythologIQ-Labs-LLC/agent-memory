"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.lexical_normalization``."""
import sys
from .runtime import lexical_normalization as _real
sys.modules[__name__] = _real
