"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.recall_observation_receipt``."""
import sys
from .runtime import recall_observation_receipt as _real
sys.modules[__name__] = _real
