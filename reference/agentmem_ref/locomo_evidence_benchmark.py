"""Compatibility alias -- this module lives at ``agentmem_ref.harness.locomo_evidence_benchmark``."""
import sys
from .harness import locomo_evidence_benchmark as _real
sys.modules[__name__] = _real
