"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.return_selection``."""
import sys
from .runtime import return_selection as _real
sys.modules[__name__] = _real
