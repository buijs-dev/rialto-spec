#!/usr/bin/env python3
"""A fake Rialto CLI for the tests of conformance.py.

    fake_cli.py validate <contract>   follows the contract's `# fake:` line, or else exits 0 for a contract without
                                      `# expect:` lines and 1, printing the codes on stderr, for one with them
    fake_cli.py diff <old> <new>      prints its arguments, `warn` on stderr, and exits with the pair's `status` file

A `# fake: exit <status> [print <text>]` line prints the text and exits with the status; `# fake: sleep` sleeps.
"""
import re
import sys
import time
from pathlib import Path

if sys.argv[1] == "diff":
    print("diff", *sys.argv[2:])
    print("warn", file=sys.stderr)
    status = Path("status")
    sys.exit(int(status.read_text()) if status.exists() else 0)

text = Path(sys.argv[-1]).read_text()
if "# fake: sleep" in text:
    time.sleep(10)
fake = re.search(r"# fake: exit (\d+)(?: print (.*))?", text)
if fake:
    print(fake.group(2) or "")
    sys.exit(int(fake.group(1)))
codes = re.findall(r"# expect: (\S+)", text)
if codes:
    print("error", *codes, file=sys.stderr)
    sys.exit(1)
