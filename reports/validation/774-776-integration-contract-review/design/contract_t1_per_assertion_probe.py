import sys, unittest
sys.path.insert(0, sys.argv[1])
from tests.test_774_governed_predecessor import _History, KILN
from tests.test_runtime_composition import _context
class T(unittest.TestCase):
    def runTest(self): pass
t = T(); h = _History(t, {"kiln": KILN}); old = tuple(h.ids["kiln"]); h.delete("kiln")
n = h.runtime.retain(h._proposal("kiln", 42), "The replacement kiln firing schedule uses cone 4 glaze.")
ad = h.runtime.adapter
print("A1 new head admitted (current):", n.fact_uuid in h.recall("replacement kiln firing schedule", "current").admitted)
print("A2 old lineage withheld (historical):", not set(old) & set(h.recall("kiln firing schedule", "historical").admitted))
print("A3 memory_deleted(new) is False:", ad.memory_deleted(n.fact_uuid) is False)
print("A4 lineage_head(new) == new:", ad.lineage_head(n.fact_uuid, _context()) == n.fact_uuid)
