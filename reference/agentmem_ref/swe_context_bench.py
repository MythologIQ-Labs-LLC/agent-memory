"""Compatibility alias -- this module lives at ``agentmem_ref.harness.swe_context_bench``."""
import sys
from .harness import swe_context_bench as _real
sys.modules[__name__] = _real
