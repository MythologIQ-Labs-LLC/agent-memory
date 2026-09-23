"""Compatibility alias -- this module lives at ``agentmem_ref.runtime.sqlite_runtime``."""
import sys
from .runtime import sqlite_runtime as _real
sys.modules[__name__] = _real
