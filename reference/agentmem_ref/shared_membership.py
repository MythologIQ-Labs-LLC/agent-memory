"""Compatibility alias -- this module lives at ``agentmem_ref.memory.shared_membership``."""
import sys
from .memory import shared_membership as _real
sys.modules[__name__] = _real
