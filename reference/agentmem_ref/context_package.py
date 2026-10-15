"""Compatibility alias -- this module lives at ``agentmem_ref.api.context_package``."""
import sys
from .api import context_package as _real
sys.modules[__name__] = _real
