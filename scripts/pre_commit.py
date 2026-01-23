#!/usr/bin/env python3
"""
Git pre-commit hook for Tuya Power Monitor.
Checks that Python code is properly formatted before committing.

Install with: invoke install-hooks
"""

import os
import subprocess
import sys

# Get uv path - check common locations
UV_PATH = None
for path in [
    os.path.expanduser("~/.local/bin/uv"),
    "/usr/local/bin/uv",
    "/usr/bin/uv",
]:
    if os.path.isfile(path):
        UV_PATH = path
        break

if UV_PATH is None:
    # Fallback to PATH
    UV_PATH = "uv"


def main():
    """Run pre-commit checks."""
    print("🔍 Running pre-commit checks...")

    # Get list of staged Python files
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )

    staged_files = [f for f in result.stdout.strip().split("\n") if f.endswith(".py") and f]

    if not staged_files:
        print("✅ No Python files to check")
        return 0

    print(f"   Checking {len(staged_files)} Python file(s)...")

    # Check formatting with ruff (using uv to ensure ruff is available)
    format_result = subprocess.run(
        [UV_PATH, "run", "ruff", "format", "--check"] + staged_files,
        capture_output=True,
        text=True,
    )

    if format_result.returncode != 0:
        print("❌ Code is not formatted. Run 'invoke format' to fix:")
        print(format_result.stdout)
        print(format_result.stderr)
        print("\nTo fix, run:")
        print("  invoke format")
        print("  git add -u")
        print("  git commit")
        return 1

    # Check linting with ruff (warn only, don't block)
    lint_result = subprocess.run(
        [UV_PATH, "run", "ruff", "check"] + staged_files,
        capture_output=True,
        text=True,
    )

    if lint_result.returncode != 0:
        print("⚠️  Linting issues found (not blocking):")
        print(lint_result.stdout)
        print("\nTo fix, run: invoke lint-fix")

    print("✅ Pre-commit checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
