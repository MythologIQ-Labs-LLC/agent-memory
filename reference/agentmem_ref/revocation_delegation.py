"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.revocation_delegation``."""
import sys
from .runtime import revocation_delegation as _real
sys.modules[__name__] = _real
