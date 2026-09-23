"""Compatibility alias -- this module lives at ``agentmem_ref.harness.retrieval_quality_benchmark``."""
import sys
from .harness import retrieval_quality_benchmark as _real
sys.modules[__name__] = _real
