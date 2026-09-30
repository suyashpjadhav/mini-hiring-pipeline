"""Single quality gate script for local checks and CI.

Runs ruff check, ruff format --check, mypy, lint-imports, pytest, secret scan,
and optional eval gate in order. Exits non-zero on first failure or prints PASS/FAIL summary table.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class StepResult(NamedTuple):
    """Result of a single check step."""

    name: str
    status: str
    details: str = ""


SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    """Run command with fixed argv and return (success, output)."""
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = (res.stdout + "\n" + res.stderr).strip()
    return res.returncode == 0, output


def scan_secrets() -> tuple[bool, str]:
    """Scan tracked git text files for secret patterns."""
    res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        return False, f"git ls-files failed: {res.stderr}"

    files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    found_leaks: list[str] = []

    for file_path in files:
        path = Path(file_path)
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeError):
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                found_leaks.append(file_path)
                break

    if found_leaks:
        return False, f"Potential secret found in files: {', '.join(found_leaks)}"
    return True, "No secrets detected."


def main() -> None:
    """Execute all quality gates in sequence."""
    results: list[StepResult] = []

    steps = [
        ("ruff check", ["uv", "run", "ruff", "check", "."]),
        ("ruff format --check", ["uv", "run", "ruff", "format", "--check", "."]),
        ("mypy", ["uv", "run", "mypy"]),
        ("lint-imports", ["uv", "run", "lint-imports"]),
        ("pytest", ["uv", "run", "pytest"]),
    ]

    failed = False

    for name, cmd in steps:
        print(f"=== Running {name} ===")
        ok, output = run_cmd(cmd)
        if output:
            print(output)
        if ok:
            results.append(StepResult(name, "PASS"))
        else:
            results.append(StepResult(name, "FAIL", output))
            failed = True
            break

    if not failed:
        print("=== Running secret scan ===")
        ok, msg = scan_secrets()
        print(msg)
        if ok:
            results.append(StepResult("secret scan", "PASS"))
        else:
            results.append(StepResult("secret scan", "FAIL", msg))
            failed = True

    if not failed:
        eval_script = Path("scripts/eval.py")
        if eval_script.exists():
            print("=== Running eval gate ===")
            ok, output = run_cmd(["uv", "run", "python", "-m", "scripts.eval", "--gate"])
            print(output)
            if ok:
                results.append(StepResult("eval gate", "PASS"))
            else:
                results.append(StepResult("eval gate", "FAIL", output))
                failed = True
        else:
            print("SKIP eval gate (Step 16)")
            results.append(StepResult("eval gate", "SKIP", "scripts/eval.py not present"))

    print("\n" + "=" * 40)
    print("QUALITY GATE SUMMARY")
    print("=" * 40)
    for r in results:
        print(f"{r.name:<25} [{r.status}]")
    print("=" * 40)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
