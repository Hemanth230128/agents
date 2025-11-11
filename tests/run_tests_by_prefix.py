#!/usr/bin/env python3
"""
Run all test files in `tests/` whose filenames start with `tests_` using pytest.

This runner invokes pytest on each matching file individually. Running files
one-by-one makes it easier to isolate failing tests and debug issues.

Usage:
    python tests/run_tests_by_prefix.py
    python tests/run_tests_by_prefix.py --pattern "tests_*.py" --pytest-args "-q -k some_marker"

Exit code: 0 when all files pass, 1 when any file fails.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_test_files(tests_dir: Path, pattern: str) -> list[Path]:
    files = sorted(tests_dir.glob(pattern))
    # Exclude this runner if it matches the pattern
    runner = Path(__file__).resolve()
    return [p for p in files if p.resolve() != runner]


def run_pytest_on_file(py_exe: str, filepath: Path, extra_args: str) -> int:
    cmd = [py_exe, "-m", "pytest", str(filepath)]
    if extra_args:
        cmd.extend(extra_args.split())
    print("\n" + "=" * 80)
    print(f"Running: {filepath.name}")
    print("Command:", " ".join(cmd))
    res = subprocess.run(cmd)
    return res.returncode


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    parser = argparse.ArgumentParser(description="Run tests_*.py files individually with pytest")
    parser.add_argument("--pattern", "-p", default="test_*.py", help="glob pattern for test files (default: test_*.py)")
    parser.add_argument("--pytest-args", "-a", default="", help="extra args to pass to pytest (quoted)")
    parser.add_argument("--tests-dir", "-d", default=None, help="directory containing test files (default: script's tests/ folder)")
    args = parser.parse_args(argv)

    # Default to the directory containing this script (tests/)
    tests_dir = Path(args.tests_dir).resolve() if args.tests_dir else Path(__file__).resolve().parent
    if not tests_dir.exists():
        print(f"Error: tests directory not found: {tests_dir}")
        return 2

    files = find_test_files(tests_dir, args.pattern)
    # If nothing matched, try common alternates to be helpful
    if not files:
        for alt in ("test_*.py", "tests_*.py"):
            if alt == args.pattern:
                continue
            files = find_test_files(tests_dir, alt)
            if files:
                print(f"No files matched '{args.pattern}', using alternate pattern '{alt}'")
                break
    if not files:
        print(f"No test files found matching {args.pattern} (or alternates) in {tests_dir}")
        return 0

    failures: list[tuple[str, int]] = []
    for f in files:
        rc = run_pytest_on_file(sys.executable, f, args.pytest_args)
        if rc != 0:
            failures.append((f.name, rc))

    print("\n" + "=" * 80)
    print(f"Ran {len(files)} test file(s). Failures: {len(failures)}")
    if failures:
        for name, code in failures:
            print(f" - {name}: exit {code}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
