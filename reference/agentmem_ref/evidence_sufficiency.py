"""Compatibility alias: the module lives at agentmem_ref.runtime.evidence_sufficiency."""
import sys
from .runtime import evidence_sufficiency as _real
sys.modules[__name__] = _real
