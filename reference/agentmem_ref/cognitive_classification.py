"""Compatibility alias -- this module lives at ``agentmem_ref.contracts.cognitive_classification``."""
import sys
from .contracts import cognitive_classification as _real
sys.modules[__name__] = _real
