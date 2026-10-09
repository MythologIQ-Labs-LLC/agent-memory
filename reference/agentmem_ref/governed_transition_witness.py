"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.governed_transition_witness``."""
import sys
from .runtime import governed_transition_witness as _real
sys.modules[__name__] = _real
