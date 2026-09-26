"""Reference test package.

Every SQLite generation published under the test suite re-reads its governance rows and
requires them to equal a full export of the in-memory governance state (#562), so any
code path whose governance change escapes incremental tracking fails loudly here.
"""

import os

os.environ.setdefault("AGENT_MEMORY_GOVERNANCE_SELF_CHECK", "1")
