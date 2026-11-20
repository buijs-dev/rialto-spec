"""Shared fixtures: a copy of the repository in a temporary directory, and a runner for the module-level tools.

check_spec.py and example_links.py are scripts that compute ROOT from their own path and run at import. The runner
executes their real source with `__file__` pointing into the copy, compiled under the real file name, so the tools
see the copy and coverage counts the lines of the real tool.
"""

import contextlib
import io
import shutil
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))


@pytest.fixture
def repo(tmp_path):
    """A copy of the specification, examples and Markdown of this repository; check_spec passes on it."""
    root = tmp_path / "repo"
    for name in ("spec", "examples", "docs"):
        shutil.copytree(ROOT / name, root / name)
    for name in ("README.md", "CONTRIBUTING.md", "GOVERNANCE.md", "CHANGELOG.md", "LICENSE", "NOTICE"):
        shutil.copy(ROOT / name, root / name)
    (root / "tools").mkdir()
    return root


def run_tool(name, root):
    """Runs tools/<name> as if it lived in root/tools; returns (exit status, stdout)."""
    source = TOOLS / name
    code = compile(source.read_text(), str(source), "exec")
    (root / "tools").mkdir(exist_ok=True)
    # Another base name than the tool's: coverage.py takes the file name from `__file__` when the base names match,
    # and from the compiled code (the real tool) when they differ.
    fake = root / "tools" / f"under-test-{name}"
    import conformance  # noqa: F401  check_spec imports it; the real module is used, not a copy
    sys.modules.pop("sample_generator", None)
    path = list(sys.path)
    out = io.StringIO()
    status = 0
    try:
        with contextlib.redirect_stdout(out):
            exec(code, {"__file__": str(fake), "__name__": "__main__"})
    except SystemExit as exit_:
        status = exit_.code
    finally:
        sys.path[:] = path
        sys.modules.pop("sample_generator", None)
    return status, out.getvalue()


def edit(path, old, new, count=1):
    """Replaces text in a file of the copy, and fails when the text is not there."""
    text = path.read_text()
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, count))
