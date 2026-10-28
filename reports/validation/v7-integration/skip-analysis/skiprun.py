"""Run the reference suite like `python -m unittest discover -s reference/tests -t reference` and record every skip."""
import json, sys, unittest
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2])
sys.path.insert(0, str(root / "reference"))
import os; os.chdir(root)
suite = unittest.defaultTestLoader.discover(str(root / "reference/tests"), top_level_dir=str(root / "reference"))
result = unittest.TextTestRunner(stream=open(os.devnull, "w"), verbosity=0).run(suite)
record = {"ran": result.testsRun, "failures": [t.id() for t, _ in result.failures], "errors": [t.id() for t, _ in result.errors],
          "skipped": sorted([[t.id(), reason] for t, reason in result.skipped]),
          "expected_failures": [t.id() for t, _ in result.expectedFailures]}
out.write_text(json.dumps(record, indent=1) + "\n")
print(record["ran"], len(record["failures"]), len(record["errors"]), len(record["skipped"]))
