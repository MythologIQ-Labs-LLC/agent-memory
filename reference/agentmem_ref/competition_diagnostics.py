"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.competition_diagnostics``."""
import sys
from .runtime import competition_diagnostics as _real
sys.modules[__name__] = _real
