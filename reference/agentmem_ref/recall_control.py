"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.recall_control``."""
import sys
from .runtime import recall_control as _real
sys.modules[__name__] = _real
