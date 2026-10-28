"""Compatibility alias -- this module lives at ``agentmem_ref.api.scoped_identity``."""
import sys
from .api import scoped_identity as _real
sys.modules[__name__] = _real
