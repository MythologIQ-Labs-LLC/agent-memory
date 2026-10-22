"""P11: a forged token (substrate.transaction() + substrate.generation_opened(), both public) followed by close()."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403

root, m = fresh()
sub = m.runtime.adapter.checkpoint_substrate()
with sub.transaction(), sub.generation_opened():
    r = m.runtime.adapter.governed_recall("deploy", m._handle_recall_context())
print("forged generation: NOT refused, committed; admitted", r.admitted)
m.close()
print("close then", try_reopen(root))
