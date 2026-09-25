"""Governed Agent Memory reference runtime and developer facade.

This package demonstrates governed paths over qualified substrates and typed
interoperability seams. It is a bounded reference/RC surface, not a production
1.0 or universal conformance claim. See `reference/README.md` for the exact
evidence and limitations.
"""

from .runtime import adapter
from .core import governance_projection, policy, receipts
from .state import substrate
from .api import surface

AgentMemory = surface.AgentMemory

__all__ = [
    "AgentMemory",
    "adapter",
    "governance_projection",
    "policy",
    "receipts",
    "substrate",
    "surface",
]
