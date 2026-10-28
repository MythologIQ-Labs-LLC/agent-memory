"""Compatibility alias -- this module lives at ``agentmem_ref.api.store_contract``."""
import sys
from .api import store_contract as _real
sys.modules[__name__] = _real
