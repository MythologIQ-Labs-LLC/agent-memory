"""#768 adversarial output-path controls for a read-only frontier projection.

Preregistered before implementation. The CLI destructive test writes only to
disposable fixture copies, never to the repository's accepted evidence.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_frontier_objectives import (  # noqa: E402
    DASHBOARD, DEFICITS, OBJECTIVES, FrontierEvidenceError,
    resolve_output_path,
)


class ReadOnlyFrontierOutputPathTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.workspace = Path(workspace.name)
        self.root = self.workspace / "fixture-repository"
        self.root.mkdir()
        self.external = self.workspace / "projection.json"

    def test_all_three_accepted_evidence_input_paths_are_refused(self):
        for relative in (OBJECTIVES, DEFICITS, DASHBOARD):
            with self.subTest(relative=relative):
                with self.assertRaisesRegex(
                    FrontierEvidenceError, "outside the source repository"
                ):
                    resolve_output_path(self.root, self.root / relative)

    def test_other_repository_paths_cannot_be_overwritten(self):
        for path in (
            self.root,
            self.root / "README.md",
            self.root / "reports" / "benchmarks" / "new.json",
            self.root / "scripts" / "build_frontier_objectives.py",
        ):
            with self.subTest(path=path), self.assertRaises(FrontierEvidenceError):
                resolve_output_path(self.root, path)

    def test_dotdot_and_existing_symlink_alias_cannot_bypass_guard(self):
        target = self.root / "reports" / "benchmarks" / "deficits"
        target.mkdir(parents=True)
        disguised = self.workspace / "aliases"
        try:
            disguised.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable in this environment")
        with self.assertRaises(FrontierEvidenceError):
            resolve_output_path(
                self.root, disguised / "reports" / "benchmarks" / "deficits" / "current.json"
            )
        with self.assertRaises(FrontierEvidenceError):
            resolve_output_path(self.root, self.root / "docs" / ".." / "README.md")

    def test_separate_output_path_remains_supported_without_side_effects(self):
        accepted = resolve_output_path(self.root, self.external)
        self.assertEqual(accepted, self.external.resolve())
        self.assertFalse(accepted.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_cli_refuses_overwriting_disposable_ledger_fixture(self):
        for source in (OBJECTIVES, DEFICITS, DASHBOARD):
            destination = self.root / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, destination)
        target = self.root / DEFICITS
        original = target.read_bytes()
        run = subprocess.run(
            [
                sys.executable, str(ROOT / "scripts" / "build_frontier_objectives.py"),
                "--root", str(self.root), "--output", str(target),
            ],
            capture_output=True, text=True, check=False, timeout=15,
        )
        self.assertNotEqual(run.returncode, 0, run.stdout)
        self.assertIn("outside the source repository", run.stderr)
        self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
