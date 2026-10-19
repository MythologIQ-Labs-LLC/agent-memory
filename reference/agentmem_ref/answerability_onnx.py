"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.answerability_onnx``."""
import sys
from .runtime import answerability_onnx as _real
sys.modules[__name__] = _real
