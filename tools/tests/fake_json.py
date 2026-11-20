#!/usr/bin/env python3
"""A fake Rialto CLI with JSON output for the tests of compare_tools.py.

    fake_json.py <tool> <contract>

prints `{"contracts": [{"diagnostics": [...]}]}` with one diagnostic per `# <tool>: {json}` line of the contract.
A `# <tool>: no-json` line prints text instead; `# <tool>: sleep` sleeps.
"""
import json
import sys
import time
from pathlib import Path

tool, contract = sys.argv[1], Path(sys.argv[2])
prefix = f"# {tool}: "
lines = [line[len(prefix):] for line in contract.read_text().splitlines() if line.startswith(prefix)]
if "sleep" in lines:
    time.sleep(10)
if "no-json" in lines:
    print("not json")
    print("broken", file=sys.stderr)
    sys.exit(3)
print(json.dumps({"contracts": [{"file": contract.name, "diagnostics": [json.loads(line) for line in lines]}]}))
sys.exit(1 if lines else 0)
