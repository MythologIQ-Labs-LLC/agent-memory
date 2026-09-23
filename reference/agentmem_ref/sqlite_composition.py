"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.sqlite_composition``."""
import sys
from .runtime import sqlite_composition as _real
sys.modules[__name__] = _real
