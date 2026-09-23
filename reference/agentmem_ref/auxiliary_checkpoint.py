"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.auxiliary_checkpoint``."""
import sys
from .runtime import auxiliary_checkpoint as _real
sys.modules[__name__] = _real
