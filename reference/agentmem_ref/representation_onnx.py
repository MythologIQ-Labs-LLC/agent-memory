"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.representation_onnx``."""
import sys
from .runtime import representation_onnx as _real
sys.modules[__name__] = _real
