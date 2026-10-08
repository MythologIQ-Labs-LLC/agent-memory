"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.proposition_extraction``."""
import sys
from .runtime import proposition_extraction as _real
sys.modules[__name__] = _real
