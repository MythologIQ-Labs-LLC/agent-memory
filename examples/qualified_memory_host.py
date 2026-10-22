"""Source-checkout example of the installable Agent Memory host activation gate.

Consumers of the wheel should import from `agentmem_ref.host_activation`.
The package implementation is the single authority for this behavior.
"""
from agentmem_ref.host_activation import UnqualifiedLegacyStoreError, open_qualified_memory

__all__ = ["UnqualifiedLegacyStoreError", "open_qualified_memory"]
