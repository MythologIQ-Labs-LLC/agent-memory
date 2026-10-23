"""Compatibility alias -- this module lives at ``agentmem_ref.core.content_terms``."""
import sys
from .core import content_terms as _real
sys.modules[__name__] = _real
