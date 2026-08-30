#!/usr/bin/env python
"""
Test runner script for CareerIntel AI.

Provides convenient commands for running different test suites.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> int:
    """Run a command and return exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="CareerIntel AI Test Runner")
    parser.add_argument(
        "suite",
        nargs="?",
        choices=["all", "unit", "integration", "e2e", "security", "agents", "api"],
        default="all",
        help="Test suite to run",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Skip coverage reporting",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure",
    )
    parser.add_argument(
        "-k", "--keyword",
        type=str,
        help="Run tests matching keyword expression",
    )
    parser.add_argument(
        "--markers",
        type=str,
        help="Run tests with specific markers (e.g., 'unit', 'integration')",
    )
    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML coverage report",
    )
    parser.add_argument(
        "--xml-report",
        action="store_true",
        help="Generate XML coverage report",
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        base_cmd.append("-v")
    
    if args.fail_fast:
        base_cmd.append("-x")
    
    if args.keyword:
        base_cmd.extend(["-k", args.keyword])
    
    if args.markers:
        base_cmd.extend(["-m", args.markers])
    
    # Coverage options
    if not args.no_cov:
        base_cmd.extend([
            "--cov=backend",
            "--cov-report=term-missing",
        ])
        if args.html_report:
            base_cmd.extend(["--cov-report=html:tests/coverage/html"])
        if args.xml_report:
            base_cmd.extend(["--cov-report=xml:tests/coverage/coverage.xml"])
    
    # Select test suite
    if args.suite == "unit":
        base_cmd.extend(["tests/unit", "-m", "unit"])
    elif args.suite == "integration":
        base_cmd.extend(["tests/integration", "-m", "integration"])
    elif args.suite == "e2e":
        base_cmd.extend(["tests/e2e", "-m", "e2e"])
    elif args.suite == "security":
        base_cmd.extend(["tests", "-m", "security"])
    elif args.suite == "agents":
        base_cmd.extend(["tests/unit/agents"])
    elif args.suite == "api":
        base_cmd.extend(["tests/integration"])
    else:
        base_cmd.extend(["tests"])
    
    return run_command(base_cmd, f"{args.suite.capitalize()} tests")


if __name__ == "__main__":
    sys.exit(main())