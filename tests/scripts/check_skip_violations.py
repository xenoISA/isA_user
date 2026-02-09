#!/usr/bin/env python3
"""
TDD Skip Policy Violation Checker

Detects improper use of pytest.skip() that hides unimplemented features.
This is a CI check to enforce the CDD/TDD skip policy.

POLICY:
- pytest.skip() is ONLY allowed for environment/dependency issues
- For unimplemented features: Let tests FAIL (RED phase)
- For known blockers: Use @pytest.mark.xfail(reason="...")

Usage:
    python tests/scripts/check_skip_violations.py [path]

Exit codes:
    0 - No violations found
    1 - Violations detected

See: docs/CDD_GUIDE.md -> "Test Anti-Patterns to Avoid"
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate skip is being used to hide unimplemented features
VIOLATION_PATTERNS = [
    r'skip.*not.*implement',
    r'skip.*TODO',
    r'skip.*WIP',
    r'skip.*pending.*implement',
    r'skip.*requires.*implementation',
    r'skip.*needs.*implement',
    r'skip.*waiting.*for.*implement',
    r'skip.*feature.*not.*ready',
    r'skip.*not.*yet.*implement',
    r'skip.*implement.*later',
    r'skip.*blocked.*by.*implement',
]

# Acceptable skip patterns (environment/dependency issues)
ACCEPTABLE_PATTERNS = [
    r'skip.*[Cc]ould not create',
    r'skip.*[Ss]ervice.*not.*running',
    r'skip.*[Cc]onnection.*failed',
    r'skip.*[Tt]imeout',
    r'skip.*[Ee]nvironment',
    r'skip.*[Dd]atabase.*not.*available',
    r'skip.*requires.*running.*service',
    r'skip.*[Nn]o.*auth.*token',
]


def find_skip_usages(file_path: Path) -> List[Tuple[int, str]]:
    """Find all pytest.skip() usages in a file."""
    usages = []
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            if 'pytest.skip(' in line or '@pytest.mark.skip' in line:
                usages.append((i, line.strip()))
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")

    return usages


def is_violation(line: str) -> bool:
    """Check if a skip usage is a TDD violation."""
    line_lower = line.lower()

    # Check if it matches any acceptable pattern
    for pattern in ACCEPTABLE_PATTERNS:
        if re.search(pattern, line_lower, re.IGNORECASE):
            return False

    # Check if it matches any violation pattern
    for pattern in VIOLATION_PATTERNS:
        if re.search(pattern, line_lower, re.IGNORECASE):
            return True

    return False


def check_directory(path: Path) -> List[Tuple[Path, int, str]]:
    """Check all Python files in a directory for skip violations."""
    violations = []

    for file_path in path.rglob('*.py'):
        # Skip this script itself
        if 'check_skip_violations' in str(file_path):
            continue

        usages = find_skip_usages(file_path)
        for line_num, line in usages:
            if is_violation(line):
                violations.append((file_path, line_num, line))

    return violations


def main():
    # Default to tests directory
    search_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('tests')

    if not search_path.exists():
        print(f"Error: Path '{search_path}' does not exist")
        sys.exit(1)

    print("=" * 70)
    print("TDD Skip Policy Violation Checker")
    print("=" * 70)
    print(f"Checking: {search_path}")
    print()

    violations = check_directory(search_path)

    if violations:
        print(f"Found {len(violations)} TDD SKIP VIOLATION(S):")
        print("-" * 70)

        for file_path, line_num, line in violations:
            print(f"\n{file_path}:{line_num}")
            print(f"  {line}")
            print()
            print("  FIX: Remove pytest.skip() and let the test FAIL (TDD RED phase)")
            print("  OR:  Use @pytest.mark.xfail(reason='...') for known blockers")

        print()
        print("=" * 70)
        print("POLICY REMINDER:")
        print("- pytest.skip() should NOT hide unimplemented features")
        print("- Let tests FAIL until implementation is complete")
        print("- See: docs/CDD_GUIDE.md -> 'Test Anti-Patterns to Avoid'")
        print("=" * 70)
        sys.exit(1)
    else:
        print("No TDD skip violations found.")
        print()

        # Also report total skip count for awareness
        all_skips = []
        for file_path in search_path.rglob('*.py'):
            if 'check_skip_violations' not in str(file_path):
                all_skips.extend(
                    (file_path, ln, line)
                    for ln, line in find_skip_usages(file_path)
                )

        if all_skips:
            print(f"Total pytest.skip() usages found: {len(all_skips)}")
            print("(All appear to be acceptable environment/dependency skips)")

        sys.exit(0)


if __name__ == '__main__':
    main()
