"""Compatibility alias -- this module lives at ``agentmem_ref.state.sqlite_substrate``."""
import sys
from .state import sqlite_substrate as _real
sys.modules[__name__] = _real
