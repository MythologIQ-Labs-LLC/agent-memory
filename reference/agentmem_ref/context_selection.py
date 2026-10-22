"""Compatibility alias -- this module lives at ``agentmem_ref.api.context_selection``."""
import sys
from .api import context_selection as _real
sys.modules[__name__] = _real
