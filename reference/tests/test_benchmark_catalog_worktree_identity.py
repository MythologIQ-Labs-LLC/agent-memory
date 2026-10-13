"""Local-only source identity and HTML freshness UI contract."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys
from pathlib import Path

# `scripts` is a repository-root package: make the root importable regardless of the
# invoking entry point (`python -m unittest discover` from the root puts the cwd on
# sys.path; `python reference/run_conformance.py` puts `reference/` there instead).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.build_benchmark_ui_catalog import _git_blob_from_bytes, _working_tree_identity


class SourceFingerprintTests(unittest.TestCase):
    def test_blob_sha_matches_git_algorithm(self):
        sample=b'{"evidence":"fixture"}\n'
        expect=hashlib.sha1(b"blob "+str(len(sample)).encode()+b"\0"+sample).hexdigest()
        self.assertEqual(_git_blob_from_bytes(sample), expect)

    def test_blob_sha_is_eol_stable_for_windows_workspaces(self):
        self.assertEqual(_git_blob_from_bytes(b'{"a":1}\r\n'),
                         _git_blob_from_bytes(b'{"a":1}\n'))

    def test_worktree_matches_real_git_tree_sha(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            subprocess.run(["git","init","-q",str(root)],check=True)
            folder=root/"normalized"
            folder.mkdir()
            for name,data in (("a.json",'{"a":1}\n'),("b.json",'{"b":2}\n')):
                (folder/name).write_text(data,encoding="utf-8")
            subprocess.run(["git","-C",str(root),"add","normalized"],check=True)
            top=subprocess.run(["git","-C",str(root),"write-tree"],check=True,text=True,capture_output=True).stdout.strip()
            out=subprocess.run(["git","-C",str(root),"ls-tree",top,"normalized"],check=True,text=True,capture_output=True).stdout.strip()
            expected=out.split()[2]
            self.assertEqual(_working_tree_identity(folder),expected)
            (folder/"b.json").write_text('{"b":3}\n',encoding="utf-8")
            self.assertNotEqual(_working_tree_identity(folder),expected)

    def test_refuses_untracked_nonjson_file_in_normalized_directory(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            (folder/"a.json").write_text("{}")
            (folder/"noise.log").write_text("not an evidence output")
            with self.assertRaisesRegex(ValueError,"normalized evidence tree"):
                _working_tree_identity(folder)


class ViewerFreshnessContract(unittest.TestCase):
    def test_refresh_panel_is_fail_closed_on_missing_manifest_or_mismatched_snapshot(self):
        html=(Path(__file__).resolve().parents[2]/"reports/benchmarks/ui/index.html").read_text(encoding="utf-8")
        self.assertIn('id="refresh-status"',html)
        self.assertIn("refreshStatus.catalog_snapshot_id !== dataset.snapshot_id",html)
        self.assertIn("STALE or invalid refresh manifest",html)
        self.assertIn("not live GitHub freshness",html)
        self.assertIn("unranked pending qualification",html)


if __name__=="__main__":
    unittest.main()
