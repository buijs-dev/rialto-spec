"""tools/conformance.py: the pass and fail rules, the expected codes, the levels, --jobs, --filter and --diff."""

import sys
from pathlib import Path

import pytest

import conformance

FAKE = str(Path(__file__).with_name("fake_cli.py"))
VALIDATE = [sys.executable, FAKE, "validate", "{contract}"]


@pytest.fixture
def contracts(tmp_path, monkeypatch):
    """Test contracts in a temporary examples/contracts, which conformance.py then runs."""
    directory = tmp_path / "contracts"
    monkeypatch.setattr(conformance, "CONTRACTS", directory)
    monkeypatch.setattr(conformance, "PAIRS", tmp_path / "compat")

    def write(name, text):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    return write


def main(monkeypatch, capsys, *args, command=VALIDATE):
    monkeypatch.setattr(sys, "argv", ["conformance.py", *args, "--", *command])
    status = conformance.main()
    return status, capsys.readouterr().out


def lines(out):
    return [line for line in out.splitlines() if line.startswith(("PASS", "FAIL"))]


# Pass and fail -------------------------------------------------------------------------------------------------


def test_every_contract_passes(contracts, monkeypatch, capsys):
    contracts("valid/a.yaml", "# capabilities: none\n")
    contracts("valid/split/contract.rialto.yaml", "a: 1\n")
    contracts("valid/split/parts/b.rialto.yaml", "not a root\n")
    contracts("invalid/b.yaml", "# expect: RIALTO-K001\n# expect: RIALTO-K002\n")
    status, out = main(monkeypatch, capsys)
    assert status == 0
    assert lines(out) == ["PASS valid/a.yaml", "PASS valid/split/contract.rialto.yaml", "PASS invalid/b.yaml"]
    assert "3 passed, 0 failed; command: " in out


@pytest.mark.parametrize("name, text, reason", [
    ("valid/a.yaml", "# fake: exit 2\n", "exit 2, expected 0"),
    ("invalid/a.yaml", "# expect: RIALTO-K001\n# fake: exit 0 print RIALTO-K001\n",
     "exit 0, expected a failure with RIALTO-K001"),
    ("invalid/a.yaml", "# expect: RIALTO-K001\n# expect: RIALTO-K002\n# fake: exit 1 print RIALTO-K002\n",
     "missing RIALTO-K001"),
    ("invalid/a.yaml", "# expect: RIALTO-K001\n# fake: exit 1 print RIALTO-K0011\n", "missing RIALTO-K001"),
    ("invalid/a.yaml", "# fake: exit 1 print RIALTO-K001\n", "names no expected code (# expect: RIALTO-…)"),
    # Only the leading comment lines name expected codes.
    ("invalid/a.yaml", "rialto: x\n# expect: RIALTO-K001\n", "names no expected code (# expect: RIALTO-…)"),
])
def test_failing_contract(contracts, monkeypatch, capsys, name, text, reason):
    contracts(name, text)
    status, out = main(monkeypatch, capsys)
    assert status == 1
    assert lines(out) == [f"FAIL {name}: {reason}"]
    assert "0 passed, 1 failed" in out


def test_timeout(contracts, monkeypatch, capsys):
    contracts("valid/a.yaml", "# fake: sleep\n")
    contracts("invalid/b.yaml", "# expect: RIALTO-K001\n# fake: sleep\n")
    status, out = main(monkeypatch, capsys, "--timeout", "1", "-v")
    assert status == 1
    assert lines(out) == ["FAIL valid/a.yaml: exit None, expected 0",
                          "FAIL invalid/b.yaml: exit None, expected a failure with RIALTO-K001"]
    assert "     timed out after 1 s" in out


def test_verbose_prints_the_output_of_failing_runs(contracts, monkeypatch, capsys):
    contracts("valid/a.yaml", "# fake: exit 1 print first words\n")
    contracts("valid/b.yaml", "# fake: exit 0 print quiet\n")
    _, out = main(monkeypatch, capsys, "-v")
    assert "     first words" in out
    assert "quiet" not in out


def test_no_contracts_is_a_failure(contracts, monkeypatch, capsys):
    status, out = main(monkeypatch, capsys)
    assert status == 1
    assert "0 passed, 0 failed" in out


# Selection -----------------------------------------------------------------------------------------------------


def three(contracts):
    contracts("valid/apple.yaml", "")
    contracts("valid/pear.yaml", "")
    contracts("invalid/apple.yaml", "# expect: RIALTO-K001\n")


def test_only(contracts, monkeypatch, capsys):
    three(contracts)
    assert lines(main(monkeypatch, capsys, "--only", "invalid")[1]) == ["PASS invalid/apple.yaml"]
    assert lines(main(monkeypatch, capsys, "--only", "valid")[1]) == ["PASS valid/apple.yaml", "PASS valid/pear.yaml"]


def test_filter_matches_the_path(contracts, monkeypatch, capsys):
    three(contracts)
    assert lines(main(monkeypatch, capsys, "--filter", "apple")[1]) == ["PASS valid/apple.yaml", "PASS invalid/apple.yaml"]
    assert lines(main(monkeypatch, capsys, "--filter", "invalid/")[1]) == ["PASS invalid/apple.yaml"]


def test_jobs_keep_the_order(contracts, monkeypatch, capsys):
    for i in range(12):
        contracts(f"valid/c{i:02}.yaml", "# fake: exit 1\n" if i % 5 == 0 else "")
    one = main(monkeypatch, capsys)
    many = main(monkeypatch, capsys, "--jobs", "6")
    zero = main(monkeypatch, capsys, "--jobs", "0")  # at least one at a time
    assert one == many == zero
    assert lines(one[1])[0] == "FAIL valid/c00.yaml: exit 1, expected 0"
    assert "9 passed, 3 failed" in one[1]


# The command ---------------------------------------------------------------------------------------------------


ECHO = [sys.executable, "-c", "import os, sys; print(os.getcwd(), *sys.argv[1:])"]


def test_contract_placeholder_and_working_directory(tmp_path):
    contract = tmp_path / "x" / "c.yaml"
    contract.parent.mkdir()
    contract.write_text("")
    status, output = conformance.run(ECHO + ["--file={contract}", "-q"], contract, 10)
    assert status == 0
    assert output.split() == [str(contract.parent.resolve()), f"--file={contract}", "-q"]
    _, appended = conformance.run(ECHO + ["-q"], contract, 10)
    assert appended.split()[1:] == ["-q", str(contract)]


def test_command_not_found(contracts, monkeypatch, capsys):
    contracts("valid/a.yaml", "")
    with pytest.raises(SystemExit, match="error: command not found: no-such-rialto"):
        main(monkeypatch, capsys, command=["no-such-rialto", "validate"])


def test_relative_program_path_is_made_absolute(contracts, monkeypatch, capsys):
    contracts("valid/a.yaml", "")
    monkeypatch.chdir(Path(FAKE).parent)
    status, out = main(monkeypatch, capsys, command=["./fake_cli.py", "validate"])
    assert status == 0, out
    assert f"command: {FAKE} validate" in out


@pytest.mark.parametrize("args", [["--only", "valid"], ["--only", "valid", "--"]])
def test_usage_without_a_command(monkeypatch, capsys, args):
    monkeypatch.setattr(sys, "argv", ["conformance.py", *args])
    assert conformance.main() == 2
    assert "error: give the command after --" in capsys.readouterr().err


# Expected codes and capabilities -------------------------------------------------------------------------------


def test_expected_codes_and_capabilities(contracts):
    path = contracts("invalid/a.yaml", "# expect: RIALTO-K001\n# capabilities: rest.server [server], "
                     "identify: member, domain.entity\n# expect: RIALTO-P002\nrialto: x\n# expect: RIALTO-K003\n")
    assert conformance.expected_codes(path) == ["RIALTO-K001", "RIALTO-P002"]
    assert conformance.capabilities(path) == [("rest.server", "server"), ("identify: member", None),
                                              ("domain.entity", None)]
    assert conformance.capabilities(contracts("valid/none.yaml", "# capabilities: none\n")) == []
    assert conformance.capabilities(contracts("valid/no-line.yaml", "rialto: x\n# capabilities: none\n")) is None


# A level accepts an entry of a profile it has not (it does not ask it), and an entry of a side it does not judge.
@pytest.mark.parametrize("entries, levels", [
    ([], {"starter", "backend", "client"}),
    ([("domain.entity", None)], {"starter", "backend", "client"}),
    ([("persistence.delete.soft", None)], {"starter", "client"}),
    ([("rest.server", "server")], {"starter", "backend", "client"}),
    ([("rest.server", None)], {"backend"}),
    ([("rest.client", "client")], {"starter", "backend", "client"}),
    ([("presentation.table", "view")], {"starter", "backend"}),
    ([("pagination: offset", None)], {"starter"}),
    ([("identify: member", None)], {"starter", "backend", "client"}),
    ([("mode: binary", None)], {"starter", "client"}),
    ([("auth.server", None), ("auth.view", None)], {"starter"}),
])
def test_within_a_level(entries, levels):
    assert {level for level in conformance.LEVELS if conformance.within(entries, level)} == levels


def level_contracts(contracts):
    contracts("valid/starter.yaml", "# capabilities: domain.entity, rest.server [server]\n")
    contracts("valid/backend.yaml", "# capabilities: persistence.read, rest.server\n")
    contracts("valid/client.yaml", "# capabilities: rest.client, pagination: cursor\n# fake: exit 1\n")
    contracts("invalid/any.yaml", "# expect: RIALTO-K001\n")


@pytest.mark.parametrize("level, names", [
    ("starter", ["valid/starter.yaml", "invalid/any.yaml"]),
    ("backend", ["valid/backend.yaml", "valid/starter.yaml", "invalid/any.yaml"]),
    ("client", ["valid/client.yaml", "valid/starter.yaml", "invalid/any.yaml"]),
])
def test_level_runs_the_contracts_within_it(contracts, monkeypatch, capsys, level, names):
    level_contracts(contracts)
    _, out = main(monkeypatch, capsys, "--level", level)
    assert [line.split()[1].rstrip(":") for line in lines(out)] == names


def test_level_all_reports_every_level(contracts, monkeypatch, capsys):
    level_contracts(contracts)
    status, out = main(monkeypatch, capsys, "--level", "all")
    assert status == 1
    assert len(lines(out)) == 4
    assert "3 passed, 1 failed" in out
    assert "level starter: 2 passed, 0 failed" in out
    assert "level backend: 3 passed, 0 failed" in out
    assert "level client: 2 passed, 1 failed" in out


# --diff ---------------------------------------------------------------------------------------------------------


DIFF = [sys.executable, FAKE, "diff"]


@pytest.fixture
def pair(tmp_path, monkeypatch):
    monkeypatch.setattr(conformance, "PAIRS", tmp_path / "compat")

    def write(name, expected=None, status=None):
        directory = tmp_path / "compat" / name
        directory.mkdir(parents=True)
        (directory / "old.rialto.yaml").write_text("")
        (directory / "new.rialto.yaml").write_text("")
        if expected is not None:
            (directory / "expected.txt").write_text(expected)
        if status is not None:
            (directory / "status").write_text(str(status))
        return directory

    return write


def test_diff_pairs(pair, monkeypatch, capsys):
    pair("a-same", "diff old.rialto.yaml new.rialto.yaml\nwarn\nexit: 0\n")
    pair("b-breaking", "diff old.rialto.yaml new.rialto.yaml\nwarn\nexit: 1\n", status=1)
    pair("c-differs", "diff old.rialto.yaml new.rialto.yaml\nwarn\nexit: 0\n", status=1)
    pair("d-no-expected")
    (pair("e-no-new").parent / "e-no-new" / "new.rialto.yaml").unlink()  # not a pair
    status, out = main(monkeypatch, capsys, "--diff", "-v", "--jobs", "3", command=DIFF)
    assert status == 1
    assert lines(out) == ["PASS a-same", "PASS b-breaking", "FAIL c-differs: output differs from expected.txt",
                          "FAIL d-no-expected: has no expected.txt"]
    assert "     -exit: 0\n     +exit: 1" in out
    assert "2 passed, 2 failed" in out


def test_diff_placeholders_filter_and_timeout(pair, monkeypatch, capsys):
    pair("swapped", "diff new.rialto.yaml old.rialto.yaml\nwarn\nexit: 0\n")
    pair("other", "")
    status, out = main(monkeypatch, capsys, "--diff", "--filter", "swap", command=DIFF + ["{new}", "{old}"])
    assert status == 0
    assert lines(out) == ["PASS swapped"]
    slow = [sys.executable, "-c", "import time; time.sleep(10)"]
    assert conformance.run_diff(slow, pair("slow"), 1) == "timed out after 1 s\n"
    with pytest.raises(SystemExit, match="command not found"):
        conformance.run_diff(["no-such-rialto"], pair("missing"), 1)


def test_diff_without_pairs_is_a_failure(pair, monkeypatch, capsys):
    status, out = main(monkeypatch, capsys, "--diff", command=DIFF)
    assert status == 1
    assert "0 passed, 0 failed" in out
