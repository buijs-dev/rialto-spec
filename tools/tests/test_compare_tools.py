"""tools/compare_tools.py: same and different findings, with and without positions and messages."""

import json
import shlex
import sys
from pathlib import Path

import pytest

import compare_tools

FAKE = str(Path(__file__).with_name("fake_json.py"))
A = shlex.join([sys.executable, FAKE, "a", "{contract}"])
B = shlex.join([sys.executable, FAKE, "b"])  # without {contract}: the path is appended


@pytest.fixture
def contracts(tmp_path, monkeypatch):
    """Contracts in a temporary repository, each with the findings `a` and `b` report for it."""
    monkeypatch.setattr(compare_tools, "ROOT", tmp_path)
    monkeypatch.setattr(compare_tools, "CONTRACTS", tmp_path / "examples" / "contracts")
    monkeypatch.setattr(compare_tools, "EXTRA", [tmp_path / "examples" / "shipment" / "shipment.rialto.yaml"])

    def write(name, a=(), b=()):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"# a: {json.dumps(f) if isinstance(f, dict) else f}\n" for f in a)
                        + "".join(f"# b: {json.dumps(f) if isinstance(f, dict) else f}\n" for f in b))
        return path

    return write


def main(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["compare_tools.py", "--a", A, "--b", B, *args])
    with pytest.raises(SystemExit) as exit_:
        compare_tools.main()
    return exit_.value.code, capsys.readouterr().out


FINDING = {"file": "c.yaml", "severity": "error", "code": "RIALTO-K004", "pointer": "/types/A", "requirement": "K1.2",
           "line": 3, "column": 5, "message": "unknown type", "hint": "declare it"}


def other(**changes):
    return dict(FINDING, **changes)


def test_same_findings(contracts, monkeypatch, capsys):
    contracts("examples/contracts/valid/a.yaml")
    contracts("examples/contracts/invalid/b.yaml", a=[FINDING], b=[FINDING])
    status, out = main(monkeypatch, capsys)
    assert status == 0
    assert out.splitlines()[:2] == ["SAME examples/contracts/valid/a.yaml", "SAME examples/contracts/invalid/b.yaml"]
    assert f"2 same, 0 different; a: {A}; b: {B}" in out


@pytest.mark.parametrize("key", ["file", "severity", "code", "pointer", "requirement"])
def test_different_findings(contracts, monkeypatch, capsys, key):
    contracts("examples/contracts/invalid/b.yaml", a=[FINDING], b=[other(**{key: "x"})])
    status, out = main(monkeypatch, capsys)
    assert status == 1
    assert "DIFF examples/contracts/invalid/b.yaml" in out
    assert f"  only a: file=c.yaml severity=error code=RIALTO-K004 pointer=/types/A requirement=K1.2" in out
    assert f"  only b: " in out and f"{key}=x" in out
    assert "0 same, 1 different" in out


def test_a_finding_reported_twice_by_one_tool(contracts, monkeypatch, capsys):
    contracts("examples/contracts/invalid/b.yaml", a=[FINDING, FINDING], b=[FINDING])
    status, out = main(monkeypatch, capsys)
    assert status == 1
    assert out.count("  only a: ") == 1
    assert "only b" not in out


def test_missing_key_is_compared_as_none(contracts, monkeypatch, capsys):
    without = {key: value for key, value in FINDING.items() if key != "requirement"}
    contracts("examples/contracts/invalid/b.yaml", a=[FINDING], b=[without])
    _, out = main(monkeypatch, capsys)
    assert "  only b: file=c.yaml severity=error code=RIALTO-K004 pointer=/types/A requirement=None" in out


def test_positions(contracts, monkeypatch, capsys):
    contracts("examples/contracts/invalid/b.yaml", a=[FINDING], b=[other(line=4)])
    assert main(monkeypatch, capsys)[0] == 0
    status, out = main(monkeypatch, capsys, "--positions")
    assert status == 1
    assert "  only a: " in out and "line=3 column=5" in out
    assert "line=4 column=5" in out
    assert "message=" not in out


def test_messages(contracts, monkeypatch, capsys):
    contracts("examples/contracts/invalid/b.yaml", a=[FINDING], b=[other(hint="another hint", line=9)])
    assert main(monkeypatch, capsys, "--positions")[0] == 1
    assert main(monkeypatch, capsys)[0] == 0
    status, out = main(monkeypatch, capsys, "--messages")
    assert status == 1
    assert "message=unknown type hint=declare it" in out
    assert "hint=another hint" in out
    assert "line=" not in out


def test_output_that_is_not_json(contracts, monkeypatch, capsys):
    contracts("examples/contracts/invalid/b.yaml", a=["no-json"], b=["no-json"])
    status, out = main(monkeypatch, capsys)
    assert status == 1
    assert "  a: no JSON on stdout (exit 3): broken" in out
    assert "  b: no JSON on stdout (exit 3): broken" in out


def test_timeout(contracts, monkeypatch, capsys):
    contracts("examples/contracts/invalid/b.yaml", a=["sleep"])
    status, out = main(monkeypatch, capsys, "--timeout", "1")
    assert status == 1
    assert "  a: timed out after 1 s" in out
    assert "  b:" not in out


def test_command_not_found(contracts, monkeypatch):
    contracts("examples/contracts/valid/a.yaml")
    monkeypatch.setattr(sys, "argv", ["compare_tools.py", "--a", "no-such-rialto {contract}", "--b", B])
    with pytest.raises(SystemExit, match="error: command not found: no-such-rialto"):
        compare_tools.main()


def test_contracts_filter_jobs_and_the_shipment_example(contracts, monkeypatch, capsys):
    for name in ("valid/a.yaml", "valid/split/contract.rialto.yaml", "invalid/c.yaml"):
        contracts(f"examples/contracts/{name}")
    contracts("examples/contracts/valid/split/parts/x.rialto.yaml")  # a fragment, not compared on its own
    _, out = main(monkeypatch, capsys, "--jobs", "3")
    assert [line.split()[1] for line in out.splitlines() if line.startswith("SAME")] == [
        "examples/contracts/valid/a.yaml", "examples/contracts/valid/split/contract.rialto.yaml",
        "examples/contracts/invalid/c.yaml"]
    contracts("examples/shipment/shipment.rialto.yaml", a=[FINDING])
    status, out = main(monkeypatch, capsys, "--filter", "shipment")
    assert status == 1
    assert out.splitlines()[0] == "DIFF examples/shipment/shipment.rialto.yaml"
    assert "0 same, 1 different" in out
