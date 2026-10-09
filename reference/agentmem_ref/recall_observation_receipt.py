"""Compatibility alias for the versioned runtime recall observation receipt."""
import sys
from .runtime import recall_observation_receipt as _real
sys.modules[__name__] = _real
