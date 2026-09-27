"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.proposition_semantics``."""
import sys
from .runtime import proposition_semantics as _real
sys.modules[__name__] = _real
