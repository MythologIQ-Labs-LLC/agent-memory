"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.checkpoint_transactions``."""
import sys
from .runtime import checkpoint_transactions as _real
sys.modules[__name__] = _real
