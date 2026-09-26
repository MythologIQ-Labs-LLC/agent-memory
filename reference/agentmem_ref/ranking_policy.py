"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.ranking_policy``."""
import sys
from .runtime import ranking_policy as _real
sys.modules[__name__] = _real
