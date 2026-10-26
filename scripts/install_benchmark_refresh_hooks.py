#!/usr/bin/env python3
"""Opt-in installation of repository-native hooks; never override another owner."""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED=".githooks"

def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--install", action="store_true", help="explicitly enable no-CI local hooks")
    args=p.parse_args()
    try:
        existing=git("config","--local","--get","core.hooksPath")
    except subprocess.CalledProcessError:
        existing=""
    if existing and existing!=EXPECTED:
        raise SystemExit("REFUSED: another hooksPath is already configured: "+existing+"; merge hook ownership manually")
    if not args.install:
        print("Configured:", existing or "(none)", " | run --install to enable local event-driven refresh")
        return
    for name in ("post-commit","post-merge","pre-push"):
        path=ROOT/EXPECTED/name
        if not path.is_file():
            raise SystemExit("REFUSED: missing hook "+str(path))
        path.chmod(path.stat().st_mode | 0o111)
    git("config","--local","core.hooksPath",EXPECTED)
    print("Installed local benchmark evidence hooks. GitHub API/cloud workspaces require their own installation.")

if __name__=="__main__":
    main()
