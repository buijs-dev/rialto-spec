#!/usr/bin/env python3
"""Runs a Rialto tool over the shared test contracts in examples/contracts, or with --diff over the
compatibility pairs in examples/compat.

    python3 tools/conformance.py -- rialto validate {contract}
    python3 tools/conformance.py --diff -- rialto diff {old} {new}

The command after `--` is run once per test contract, with `{contract}` replaced by its absolute path
(appended when the command has no `{contract}`). A contract over several files is passed as its root,
`contract.rialto.yaml`.

- A valid contract passes when the command exits with 0.
- An invalid contract passes when the command exits with a status other than 0 and its output
  (stdout and stderr) contains every code its leading `# expect: RIALTO-…` lines name.
- With --level starter, backend or client, only the test contracts within that conformance level run
  (spec/generators.md#conformance-levels), judged by their leading `# capabilities: …` line as tooling judges a
  generator that implements exactly the level (C8.3): of the entries of the level's profiles, those of its side
  (`rest.server [server]`) and those without a side must be in the level; other sides and other profiles are not
  asked. --level starter judges both Starter (server) and Starter (client). A contract without the line (an invalid
  one that has no contract model) runs at every level.

With --level all, every test contract runs once, and the summary gives the result of the whole set and of each
level, as separate runs with --level would.

With --jobs N, N contracts or pairs run at a time (default 1); the report keeps their order. Use it only for a
command whose runs share nothing, such as `validate`: a generator that writes every run to the same output directory
must run one at a time.

With --diff, the command is run once per pair, in the pair's directory, with `{old}` and `{new}`
replaced by `old.rialto.yaml` and `new.rialto.yaml` (appended in that order when the command has
neither). A pair passes when its stdout, then its stderr, then a last line `exit: <status>` equal
`expected.txt` byte for byte.

Exit status 0 when every test contract or pair passes, 1 otherwise, 2 on wrong usage.
"""

import argparse
import os
from concurrent.futures import ThreadPoolExecutor
import difflib
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "examples" / "contracts"
PAIRS = ROOT / "examples" / "compat"
EXPECT = re.compile(r"# expect: (RIALTO-[A-Z]\d{3})")
CAPABILITIES = re.compile(r"# capabilities: (.+)")

# The conformance levels (spec/generators.md#conformance-levels); tools/check_spec.py checks them against the table.
# Strategies are written as there, `<concern>: <strategy>`.
STARTER_SERVER = {
    "domain.entity", "domain.value-object", "domain.shape", "mapping.enum", "mapping.wrapper",
    "mapping.direction.reverse", "rest.model", "rest.server", "errors.server",
}
STARTER_CLIENT = {"rest.model", "rest.client", "errors.client"}
BACKEND = STARTER_SERVER | {
    "persistence.read", "persistence.insert", "persistence.partial-update", "persistence.delete.physical",
    "persistence.optimistic-concurrency", "domain.shape.partial", "mapping.partial", "query.filter.rsql", "query.sort.colon", "query.pagination.cursor",
    "lifecycle.create", "lifecycle.update.merge-patch", "lifecycle.delete", "auth.server", "events.publish",
    "events.mode.structured",
}
CLIENT = STARTER_CLIENT | {
    "query.filter.rsql", "query.sort.colon", "query.pagination.cursor", "auth.client.authorization-code",
    "auth.view", "errors.view", "presentation.read-view", "presentation.form", "presentation.action",
    "presentation.list", "presentation.navigation",
}
STARTER_STRATEGIES = {"identify: member", "location: pointer"}
CLIENT_STRATEGIES = STARTER_STRATEGIES | {"pagination: cursor", "filter: rsql", "sort: colon", "update: merge-patch"}
BACKEND_STRATEGIES = CLIENT_STRATEGIES | {"mode: structured"}

# What tooling asks of a generator that implements exactly a level (C8.3): its capabilities, strategies and sides.
# Starter is judged for both sides: a test contract runs at --level starter when it is within both Starters.
LEVELS = {
    "starter": [(STARTER_SERVER, STARTER_STRATEGIES, {"server"}), (STARTER_CLIENT, STARTER_STRATEGIES, {"client"})],
    "backend": [(BACKEND, BACKEND_STRATEGIES, {"server"})],
    "client": [(CLIENT, CLIENT_STRATEGIES, {"client", "view"})],
}
# The profile of a strategy, by its concern.
STRATEGY_PROFILES = {
    "pagination": "query", "filter": "query", "sort": "query", "update": "lifecycle",
    "identify": "errors", "location": "errors", "mode": "events", "transport": "events",
}
ENTRY = re.compile(r"(\S+(?:: \S+)?)(?: \[(server|client|view)\])?$")


def capabilities(path):
    """The entries of a test contract's `# capabilities:` line, as (name, side or None); None without the line."""
    for line in path.read_text().splitlines():
        if not line.startswith("#"):
            break
        match = CAPABILITIES.match(line)
        if match:
            if match.group(1).strip() == "none":
                return []
            return [ENTRY.match(entry.strip()).groups() for entry in match.group(1).split(",")]
    return None


def within(entries, level):
    """Whether tooling accepts the entries for a generator of the level, on every side the level judges."""
    for capabilities_, strategies, sides in LEVELS[level]:
        profiles = {name.split(".")[0] for name in capabilities_}
        for name, side in entries:
            if ": " in name:
                if STRATEGY_PROFILES[name.split(":")[0]] in profiles and name not in strategies:
                    return False
            elif name.split(".")[0] in profiles and (side is None or side in sides) and name not in capabilities_:
                return False
    return True


def test_contracts(kind):
    """The test contracts of `valid` or `invalid`: single files, and roots of contracts over several files."""
    directory = CONTRACTS / kind
    files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*/contract.rialto.yaml"))
    return sorted(files, key=lambda path: path.relative_to(directory).as_posix())


def expected_codes(path):
    """The codes named by the leading comment lines of an invalid test contract."""
    codes = []
    for line in path.read_text().splitlines():
        if not line.startswith("#"):
            break
        match = EXPECT.match(line)
        if match:
            codes.append(match.group(1))
    return codes


def run(command, contract, timeout):
    """Runs the command for one contract; returns its exit status and combined output."""
    args = [part.replace("{contract}", str(contract)) for part in command]
    if not any("{contract}" in part for part in command):
        args.append(str(contract))
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=contract.parent)
    except FileNotFoundError:
        sys.exit(f"error: command not found: {args[0]}")
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout} s"
    return result.returncode, result.stdout + result.stderr


def pairs():
    """The compatibility pairs: directories of examples/compat with an old and a new contract."""
    return sorted(path.parent for path in PAIRS.glob("*/old.rialto.yaml") if (path.parent / "new.rialto.yaml").exists())


def run_diff(command, pair, timeout):
    """Runs the command for one pair; returns its stdout, then stderr, then `exit: <status>`."""
    names = {"{old}": "old.rialto.yaml", "{new}": "new.rialto.yaml"}
    args = []
    for part in command:
        for placeholder, name in names.items():
            part = part.replace(placeholder, name)
        args.append(part)
    if not any(placeholder in part for part in command for placeholder in names):
        args += list(names.values())
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=pair)
    except FileNotFoundError:
        sys.exit(f"error: command not found: {args[0]}")
    except subprocess.TimeoutExpired:
        return f"timed out after {timeout} s\n"
    return f"{result.stdout}{result.stderr}exit: {result.returncode}\n"


def diff_mode(command, options):
    """Compares the output of the command for every pair with its expected.txt."""
    passed = failed = 0
    selected = [pair for pair in pairs() if options.filter in pair.name]
    with ThreadPoolExecutor(options.jobs) as pool:
        outputs = list(pool.map(lambda pair: run_diff(command, pair, options.timeout), selected))
    for pair, output in zip(selected, outputs):
        name = pair.name
        expected_file = pair / "expected.txt"
        if not expected_file.exists():
            reason = "has no expected.txt"
            expected = ""
        else:
            expected = expected_file.read_text()
            reason = None if output == expected else "output differs from expected.txt"
        if reason is None:
            passed += 1
            print(f"PASS {name}")
        else:
            failed += 1
            print(f"FAIL {name}: {reason}")
            if options.verbose:
                lines = difflib.unified_diff(
                    expected.splitlines(), output.splitlines(), "expected.txt", "output", lineterm=""
                )
                print("\n".join("     " + line for line in lines))

    print(f"\n{passed} passed, {failed} failed; command: {shlex.join(command)}")
    return 0 if failed == 0 and passed > 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="Runs a Rialto tool over the shared test contracts.",
        usage="%(prog)s [options] -- <command> [args with {contract}, or with --diff {old} {new}]",
    )
    parser.add_argument("--diff", action="store_true", help="run the compatibility pairs of examples/compat")
    parser.add_argument("--only", choices=["valid", "invalid"], help="run one kind of test contract")
    parser.add_argument("--filter", default="", help="run only test contracts whose path contains this text")
    parser.add_argument(
        "--level", choices=sorted(LEVELS) + ["all"],
        help="run only the test contracts of a conformance level; all: run once and report every level",
    )
    parser.add_argument(
        "--jobs", type=int, default=1,
        help=f"test contracts or pairs run at a time (default 1; this machine has {os.cpu_count()} CPUs)",
    )
    parser.add_argument("--timeout", type=int, default=60, help="seconds per test contract or pair (default 60)")
    parser.add_argument("-v", "--verbose", action="store_true", help="print the output (with --diff: the difference) of failing runs")
    argv = sys.argv[1:]
    if "--" not in argv or argv.index("--") == len(argv) - 1:
        parser.print_usage(sys.stderr)
        print("error: give the command after --", file=sys.stderr)
        return 2
    split = argv.index("--")
    options = parser.parse_args(argv[:split])
    command = argv[split + 1:]
    # The command runs next to each contract, so a relative program path is made absolute first.
    if "/" in command[0] and Path(command[0]).exists():
        command[0] = str(Path(command[0]).resolve())
    if options.diff:
        return diff_mode(command, options)

    kinds = [options.only] if options.only else ["valid", "invalid"]
    selected = []
    for kind in kinds:
        for contract in test_contracts(kind):
            name = contract.relative_to(CONTRACTS).as_posix()
            if options.filter not in name:
                continue
            single = options.level not in (None, "all")
            if single and not within(capabilities(contract) or [], options.level):
                continue
            selected.append((kind, name, contract))

    with ThreadPoolExecutor(max(1, options.jobs)) as pool:
        results = list(pool.map(lambda item: run(command, item[2], options.timeout), selected))

    passed = failed = 0
    tally = {level: [0, 0] for level in LEVELS}
    for (kind, name, contract), (status, output) in zip(selected, results):
        reason = judge(kind, contract, status, output)
        if reason is None:
            passed += 1
            print(f"PASS {name}")
        else:
            failed += 1
            print(f"FAIL {name}: {reason}")
            if options.verbose:
                print("\n".join("     " + line for line in output.strip().splitlines()))
        if options.level == "all":
            for level in LEVELS:
                if within(capabilities(contract) or [], level):
                    tally[level][0 if reason is None else 1] += 1

    print(f"\n{passed} passed, {failed} failed; command: {shlex.join(command)}")
    if options.level == "all":
        for level, (level_passed, level_failed) in tally.items():
            print(f"level {level}: {level_passed} passed, {level_failed} failed")
    return 0 if failed == 0 and passed > 0 else 1


def judge(kind, contract, status, output):
    """Why a test contract failed, or None when it passed."""
    if kind == "valid":
        return None if status == 0 else f"exit {status}, expected 0"
    codes = expected_codes(contract)
    missing = [code for code in codes if not re.search(rf"\b{code}\b", output)]
    if not codes:
        return "names no expected code (# expect: RIALTO-…)"
    if status in (0, None):
        return f"exit {status}, expected a failure with {', '.join(codes)}"
    if missing:
        return f"missing {', '.join(missing)}"
    return None

if __name__ == "__main__":
    sys.exit(main())
