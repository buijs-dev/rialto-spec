#!/usr/bin/env python3
"""Compares the findings of two Rialto tools over the shared test contracts in examples/contracts, and the Shipment
example, field by field.

    python3 tools/compare_tools.py --a 'rialto-jvm validate --format json {contract}' \\
        --b 'rialto-dart validate --format json {contract}'

tools/conformance.py checks that each tool reports the expected codes; two tools can still disagree on where a finding
is, or which requirement it names (K1.5). This tool runs both commands per contract, reads the machine-readable output
(spec/contract.md#standard-diagnostic-codes) and reports every finding that one tool reports and the other does not.
A finding is compared by file, severity, code, pointer and requirement; --positions adds line and column, --messages
adds message and hint, which are free text and differ between tools by design.

Exit status 0 when both tools agree on every contract, 1 otherwise, 2 on wrong usage.
"""

import argparse
import json
import shlex
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "examples" / "contracts"
EXTRA = [ROOT / "examples" / "shipment" / "shipment.rialto.yaml", ROOT / "examples" / "shipment" / "split" / "shipment.rialto.yaml"]


def contracts():
    """Every test contract, valid and invalid, plus both forms of the Shipment example."""
    found = []
    for kind in ("valid", "invalid"):
        directory = CONTRACTS / kind
        found += sorted(directory.glob("*.yaml")) + sorted(directory.glob("*/contract.rialto.yaml"))
    return found + [path for path in EXTRA if path.exists()]  # the Shipment example follows in a later slice


def findings(command, contract, options):
    """The findings of one command for one contract, as a Counter of comparable tuples, or an error text."""
    args = [part.replace("{contract}", str(contract)) for part in command]
    if not any("{contract}" in part for part in command):
        args.append(str(contract))
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=options.timeout, cwd=contract.parent)
    except FileNotFoundError:
        sys.exit(f"error: command not found: {args[0]}")
    except subprocess.TimeoutExpired:
        return None, f"timed out after {options.timeout} s"
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, f"no JSON on stdout (exit {result.returncode}): {result.stderr.strip()[:200]}"
    keys = ["file", "severity", "code", "pointer", "requirement"]
    if options.positions:
        keys += ["line", "column"]
    if options.messages:
        keys += ["message", "hint"]
    found = Counter()
    for entry in document.get("contracts", []):
        for diagnostic in entry.get("diagnostics", []):
            found[tuple((key, diagnostic.get(key)) for key in keys)] += 1
    return found, None


def show(finding):
    return " ".join(f"{key}={value}" for key, value in finding)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a", required=True, help="the first command, with {contract}")
    parser.add_argument("--b", required=True, help="the second command, with {contract}")
    parser.add_argument("--positions", action="store_true", help="also compare line and column")
    parser.add_argument("--messages", action="store_true", help="also compare message and hint")
    parser.add_argument("--filter", default="", help="only contracts whose path contains this text")
    parser.add_argument("--jobs", type=int, default=1, help="contracts compared at a time")
    parser.add_argument("--timeout", type=int, default=120, help="seconds per run")
    options = parser.parse_args()
    a, b = shlex.split(options.a), shlex.split(options.b)

    selected = [c for c in contracts() if options.filter in c.relative_to(ROOT).as_posix()]

    def compare(contract):
        (found_a, error_a), (found_b, error_b) = findings(a, contract, options), findings(b, contract, options)
        if error_a or error_b:
            return [f"  a: {error_a}"] * bool(error_a) + [f"  b: {error_b}"] * bool(error_b)
        lines = [f"  only a: {show(f)}" for f in sorted((found_a - found_b).elements())]
        return lines + [f"  only b: {show(f)}" for f in sorted((found_b - found_a).elements())]

    with ThreadPoolExecutor(max_workers=max(1, options.jobs)) as pool:
        results = list(pool.map(compare, selected))

    differing = 0
    for contract, lines in zip(selected, results):
        name = contract.relative_to(ROOT).as_posix()
        if lines:
            differing += 1
            print(f"DIFF {name}")
            print("\n".join(lines))
        else:
            print(f"SAME {name}")
    print(f"\n{len(selected) - differing} same, {differing} different; a: {options.a}; b: {options.b}")
    sys.exit(1 if differing else 0)


if __name__ == "__main__":
    main()
