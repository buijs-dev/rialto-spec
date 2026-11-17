"""tools/example_links.py: the Examples lines it writes, idempotence, and what it writes for missing examples."""

import re

from conftest import ROOT, edit, run_tool


def links(root):
    status, out = run_tool("example_links.py", root)
    assert status == 0, out
    return out


def examples_line(path, group):
    match = re.search(rf"^##+ {group}\. [^\n]*\n\n(Examples: [^\n]*)", path.read_text(), re.M)
    return match and match.group(1)


def without_examples_lines(path):
    path.write_text(re.sub(r"\n\nExamples: [^\n]*", "", path.read_text()))


def test_the_repository_is_up_to_date_and_a_second_run_changes_nothing(repo):
    out = links(repo)
    assert out.startswith("groups with examples: ")
    for name in ("core.md", "contract.md"):
        assert (repo / "spec" / name).read_text() == (ROOT / "spec" / name).read_text()
    assert links(repo) == out
    for name in ("core.md", "contract.md"):
        assert (repo / "spec" / name).read_text() == (ROOT / "spec" / name).read_text()
    assert run_tool("check_spec.py", repo)[0] == 0


def test_writes_the_lines_again_after_they_are_removed(repo):
    core = repo / "spec" / "core.md"
    without_examples_lines(core)
    assert examples_line(core, "C1") is None
    links(repo)
    assert core.read_text() == (ROOT / "spec" / "core.md").read_text()


def test_missing_examples_while_the_shipment_example_is_not_there(repo):
    core = repo / "spec" / "core.md"
    without_examples_lines(core)
    links(repo)
    assert examples_line(core, "C1") == "Examples: none yet: the scenarios of the Shipment example follow in a later slice."
    assert examples_line(core, "C7") == "Examples: none: these requirements apply to the specification itself."
    assert examples_line(core, "C5").startswith("Examples: test contracts [`invalid/")
    assert "[`invalid/fragment-version/`](../examples/contracts/invalid/fragment-version/)" in examples_line(core, "C5")


def shipment_readme(root, rows=""):
    (root / "examples" / "shipment").mkdir(parents=True)
    (root / "examples" / "shipment" / "README.md").write_text(f"# Shipment\n\n| Id | Scenario | Requirements |\n|---|---|---|\n{rows}")


def test_missing_examples_once_the_shipment_example_is_there(repo):
    shipment_readme(repo)
    core = repo / "spec" / "core.md"
    without_examples_lines(core)
    links(repo)
    assert examples_line(core, "C1") is None  # no PENDING any more: the group simply has no Examples line
    assert examples_line(core, "C7").startswith("Examples: none: ")


def test_scenarios_compatibility_pairs_and_tools(repo):
    shipment_readme(repo, "| S02 | Ship | C1.2, K2.1 |\n| S01 | Order | C1.4 |\n| X1 | Not a scenario | C2.1 |\n")
    (repo / "examples" / "compat").mkdir()
    (repo / "examples" / "compat" / "README.md").write_text(
        "| Pair | Requirements |\n|---|---|\n| [`add-field`](add-field/) | C1.3 |\n")
    core = repo / "spec" / "core.md"
    edit(core, "## Rationale", "## C9. Generator protocol\n\n## Rationale")
    links(repo)
    assert examples_line(core, "C1") == (
        "Examples: scenarios S01, S02 of the [Shipment example](../examples/shipment/README.md#6-scenarios); "
        "compatibility pairs [`add-field`](../examples/compat/add-field/).")
    assert examples_line(core, "C2") is None
    assert examples_line(core, "C9") == (
        "Examples: the sample generator [`tools/sample_generator.py`](../tools/sample_generator.py), "
        "checked with [`tools/protocol_check.py`](../tools/protocol_check.py).")
    assert "scenarios S02 of the [Shipment example]" in examples_line(repo / "spec" / "contract.md", "K2")


def test_profile_and_listed_valid_test_contracts(repo):
    (repo / "spec" / "profiles").mkdir()
    query = repo / "spec" / "profiles" / "query.md"
    query.write_text("# Query\n\nThe requirements use the prefix Q here.\n\n### Q1. Lists\n\n- **Q1.1** x\n\n### Q2. Other\n")
    (repo / "examples" / "contracts" / "valid" / "list.yaml").write_text("")
    links(repo)
    assert examples_line(query, "Q1") == (
        "Examples: test contracts [`valid/list.yaml`](../../examples/contracts/valid/list.yaml).")
    assert examples_line(query, "Q2") == (
        "Examples: none yet: the scenarios of the Shipment example follow in a later slice.")


def test_invalid_test_contract_without_expected_code_is_skipped(repo):
    # check_spec reports the missing `# expect:` line; example_links links the contract nowhere and goes on.
    edit(repo / "examples" / "contracts" / "invalid" / "map-key.yaml", "# expect: RIALTO-K006\n", "")
    links(repo)
    contract = repo / "spec" / "contract.md"
    assert "invalid/map-key.yaml" not in contract.read_text()
    assert examples_line(contract, "K1").endswith("[`valid/minimal.yaml`](../examples/contracts/valid/minimal.yaml).")
