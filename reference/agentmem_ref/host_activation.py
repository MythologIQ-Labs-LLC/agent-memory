"""Compatibility alias -- this module lives at ``agentmem_ref.api.host_activation``."""
import sys
from .api import host_activation as _real
sys.modules[__name__] = _real
