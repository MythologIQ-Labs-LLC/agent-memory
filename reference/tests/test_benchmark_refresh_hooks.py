"""Static hook regressions: source changes gate, generated files and code-only pushes do not."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HOOKS=ROOT/".githooks"


class BenchmarkHookTests(unittest.TestCase):
    def test_predicate_coverage(self):
        positives=[
            "reports/benchmarks/amb/v7/row/evidence.json",
            "reports/benchmarks/dashboard/current.json",
            "reports/benchmarks/longmemeval/v8/raw.json",
            "reference/agentmem_ref/evaluation/lanes/suite-v8.json",
            "reference/agentmem_ref/evaluation/integrations/amb.json",
            "scripts/build_benchmark_frontier_leaderboards.py",
            "scripts/build_benchmark_scorecards.py",
            "reference/agentmem_ref/evaluation/ui_frontier_leaderboard.py",
        ]
        negatives=[
            "reference/agentmem_ref/runtime/adapter.py",
            "docs/README.md",
            "reports/benchmarks/ui/refresh-status.json",
            "reports/benchmarks/normalized/snapshot.json",
            "reports/benchmarks/scorecards/scorecards.json",
        ]
        for p in positives+negatives:
            cmd=' . .githooks/benchmark-refresh-paths.sh; printf "%s\\n" "$P" | benchmark_refresh_paths'
            r=subprocess.run(["sh","-c",cmd],cwd=ROOT,env={"PATH": "/usr/bin:/bin", "P":p},
                             capture_output=True,text=True)
            self.assertEqual(r.returncode,0 if p in positives else 1,p)

    def test_pre_push_only_gates_changed_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            subprocess.run(["git","init","-q","-b","main",str(root)],check=True)
            (root/".githooks").mkdir()
            for name in ("pre-push","benchmark-refresh-paths.sh"):
                (root/".githooks"/name).write_bytes((HOOKS/name).read_bytes())
            def cmd(*args,input=None):
                return subprocess.run(["git","-C",str(root),*args],input=input,text=True,
                                      capture_output=True,check=True).stdout.strip()
            (root/"README.md").write_text("hello\n")
            cmd("add",".")
            cmd("-c","user.email=test@example.invalid","-c","user.name=Tester","commit","-qm","base")
            base=cmd("rev-parse","HEAD")
            (root/"README.md").write_text("world\n")
            cmd("add",".")
            cmd("-c","user.email=test@example.invalid","-c","user.name=Tester","commit","-qm","docs")
            other=cmd("rev-parse","HEAD")
            input_text=f"refs/heads/main {other} refs/heads/main {base}\n"
            result=subprocess.run(["sh",str(root/".githooks/pre-push")],cwd=root,
                                  input=input_text,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            (root/"reports/benchmarks/amb/v8").mkdir(parents=True)
            (root/"reports/benchmarks/amb/v8/evidence.json").write_text("{}\n")
            cmd("add",".")
            cmd("-c","user.email=test@example.invalid","-c","user.name=Tester","commit","-qm","source")
            changed=cmd("rev-parse","HEAD")
            result=subprocess.run(["sh",str(root/".githooks/pre-push")],cwd=root,
                        input=f"refs/heads/main {changed} refs/heads/main {base}\n",
                        text=True,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn("benchmark publication BLOCKED",result.stderr)

    def test_git_merge_of_source_change_writes_companion_commit(self):
        """`git merge` runs post-merge, not post-commit; a merged source change must still refresh."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            subprocess.run(["git","init","-q","-b","main",str(root)],check=True)
            (root/".githooks").mkdir()
            for name in HOOKS.iterdir():
                if name.is_file():
                    target=root/".githooks"/name.name
                    target.write_bytes(name.read_bytes())
                    target.chmod(0o755)
            (root/"scripts").mkdir()
            (root/"scripts/refresh_benchmark_pages.py").write_text(
                "import pathlib,sys\n"
                "out=pathlib.Path('reports/benchmarks/ui'); out.mkdir(parents=True, exist_ok=True)\n"
                "(out/'refresh-status.json').write_text('{\"stub\": true}\\n')\n", encoding="utf-8")
            def cmd(*args):
                return subprocess.run(["git","-C",str(root),"-c","user.email=test@example.invalid","-c","user.name=Tester",*args],
                                      text=True,capture_output=True,check=True).stdout.strip()
            (root/"README.md").write_text("hello\n")
            # The hook stages the three generated trees; seed them as the real repository has them.
            for seed in ("reports/benchmarks/normalized/seed.json","reports/benchmarks/scorecards/seed.md"):
                (root/seed).parent.mkdir(parents=True,exist_ok=True)
                (root/seed).write_text("seed\n")
            cmd("add",".")
            cmd("commit","-qm","base")
            cmd("config","core.hooksPath",".githooks")
            cmd("checkout","-q","-b","evidence")
            (root/"reports/benchmarks/amb/v9").mkdir(parents=True)
            (root/"reports/benchmarks/amb/v9/evidence.json").write_text("{}\n")
            cmd("add",".")
            cmd("-c","core.hooksPath=/dev/null","commit","-qm","record evidence elsewhere")
            cmd("checkout","-q","main")
            (root/"README.md").write_text("diverged\n")
            cmd("add",".")
            cmd("commit","-qm","docs")
            cmd("merge","--no-ff","-q","-m","merge evidence","evidence")
            subject=cmd("log","-1","--format=%s")
            self.assertEqual(subject,"chore(benchmarks): refresh recorded evidence projections [skip ci]",
                             cmd("log","--oneline","-5"))
            self.assertEqual(cmd("show","--format=","--name-only","HEAD"),"reports/benchmarks/ui/refresh-status.json")
            self.assertEqual(cmd("status","--porcelain"),"")


if __name__=="__main__":
    unittest.main()
