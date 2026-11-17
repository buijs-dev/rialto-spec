"""tools/check_spec.py: each check passes on a consistent copy of the repository and fails on a broken one."""

import json
import sys

import pytest

import conformance
from conftest import ROOT, edit, run_tool

# The tests copy the repository; these depend on what a later slice adds.
LATER_DOMAIN = pytest.mark.skipif((ROOT / "spec" / "profiles" / "domain.md").exists(),
                                  reason="the domain profile is there; the test adds one of its own")
LATER_GENERATORS = pytest.mark.skipif((ROOT / "spec" / "generators.md").exists(),
                                      reason="spec/generators.md is there; the test writes one of its own")


def check(root):
    return run_tool("check_spec.py", root)


def assert_fails(root, *messages):
    status, out = check(root)
    assert status == 1, out
    for message in messages:
        assert message in out, out
    return out


# The repository as it is, and what exists ------------------------------------------------------------------------


def test_passes_on_the_repository(repo):
    status, out = check(repo)
    assert status == 0, out
    assert out.startswith("note: spec/generators.md is not there yet") == (not (ROOT / "spec" / "generators.md").exists())
    assert "requirements, all checks passed." in out


@LATER_DOMAIN
def test_references_to_documents_of_later_slices_are_accepted(repo):
    # The domain profile (prefix D) does not exist yet, so D9.1 may be named; core (prefix C) exists, so C99.1 may not.
    (repo / "docs" / "later.md").write_text("# Later\n\nSee D9.1 and C99.1.\n")
    out = assert_fails(repo, "docs/later.md: reference to unknown requirement C99.1")
    assert "D9.1" not in out


def test_without_pyyaml_the_schema_checks_are_skipped(repo, monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)
    (repo / "examples" / "contracts" / "valid" / "minimal.yaml").write_text('rialto: "1.0.0"\nentities: {}\n')
    status, out = check(repo)
    assert status == 0, out
    assert "install pyyaml and jsonschema" in out


# 1-2. Requirements and key words -----------------------------------------------------------------------------


def test_identifier_with_the_prefix_of_another_document(repo):
    edit(repo / "spec" / "core.md", "- **C1.1** ", "- **K1.1** ")
    assert_fails(repo, "spec/core.md: K1.1: identifier does not use prefix C", "K1.1: duplicate identifier")


def test_identifiers_are_sequential(repo):
    edit(repo / "spec" / "core.md", "- **C1.2** ", "- **C1.9** ")
    assert_fails(repo, "C1: expected sequential identifiers")


def test_lowercase_key_word(repo):
    edit(repo / "spec" / "core.md", "Cleanup MUST remove", "Cleanup must remove")
    assert_fails(repo, "C1.5: lowercase key word 'must'")


def test_key_words_in_code_are_ignored(repo):
    edit(repo / "spec" / "core.md", "Cleanup MUST remove", "Cleanup `must` MUST remove")
    assert check(repo)[0] == 0


def test_mixed_case_key_word(repo):
    edit(repo / "spec" / "core.md", "Cleanup MUST remove", "Cleanup MUST not keep")
    assert_fails(repo, "C1.5: mixed-case key word 'MUST not'")


# 2b. Diagnostic codes ----------------------------------------------------------------------------------------


def test_diagnostic_table_missing(repo):
    edit(repo / "spec" / "contract.md", "## Standard diagnostic codes\n", "## Codes\n")
    assert_fails(repo, "Standard diagnostic codes table missing")


def test_invalid_and_duplicate_diagnostic_codes(repo):
    edit(repo / "spec" / "contract.md", "| `RIALTO-S005` |", "| `RIALTO-X005` |")
    edit(repo / "spec" / "contract.md", "| `RIALTO-S004` |", "| `RIALTO-S003` |")
    assert_fails(repo, "invalid diagnostic code 'RIALTO-X005'", "duplicate diagnostic code 'RIALTO-S003'")


def test_invalid_test_contract_without_expected_code(repo):
    edit(repo / "examples" / "contracts" / "invalid" / "unknown-key.yaml", "# expect: RIALTO-K002\n", "")
    assert_fails(repo, "unknown-key.yaml: missing '# expect: RIALTO-...' on first line")


def test_invalid_test_contract_with_undocumented_code(repo):
    edit(repo / "examples" / "contracts" / "invalid" / "unknown-key.yaml", "RIALTO-K002", "RIALTO-K999")
    assert_fails(repo, "unknown-key.yaml: expects undocumented diagnostic code 'RIALTO-K999'")


# 3, 5, 6. References, terminology and links ------------------------------------------------------------------


def test_reference_to_unknown_requirement(repo):
    (repo / "docs" / "notes.md").write_text("# Notes\n\nSee C1.99, not `C1.98` in code.\n")
    out = assert_fails(repo, "docs/notes.md: reference to unknown requirement C1.99")
    assert "C1.98" not in out


@pytest.mark.parametrize("text, line", [
    ("A binding.\n", "'binding' without operation, field or protocol"),
    ("\nUI bindings.\n", "line 2: 'bindings' without operation, field or protocol"),
])
def test_bare_binding(repo, text, line):
    (repo / "docs" / "terms.md").write_text(text)
    assert_fails(repo, "docs/terms.md: ", line)


def test_qualified_quoted_and_code_bindings_are_accepted(repo):
    (repo / "docs" / "terms.md").write_text(
        'A field binding, an operation binding, protocol bindings, the word "binding" and `binding` in code.\n')
    assert check(repo)[0] == 0


def test_forbidden_names_in_the_specification(repo):
    (repo / "spec" / "notes.md").write_text("# Notes\n\nLike fabrio and `StrataStaX` did.\n")
    assert_fails(repo, "spec/notes.md: mentions 'fabrio'", "spec/notes.md: mentions 'StrataStaX'")


def test_forbidden_names_outside_the_specification_are_accepted(repo):
    (repo / "docs" / "notes.md").write_text("# Notes\n\nFabrio.\n")
    assert check(repo)[0] == 0


def test_links_and_anchors(repo):
    (repo / "docs" / "links.md").write_text(
        "# Links\n\n## Here\n\n[ok](../spec/core.md#c1-generated-and-authored-code) [self](#here) "
        "[web](https://example.com/x.md) [file](../spec/contract-1.0.0.schema.json#anything)\n"
        "[gone](missing.md) [bad](../spec/core.md#nowhere) [badself](#there)\n")
    out = assert_fails(repo, "broken link missing.md", "broken anchor ../spec/core.md#nowhere", "broken anchor #there")
    assert out.count("docs/links.md") == 3


def test_markdown_under_a_directory_named_site_is_checked(tmp_path, repo):
    # The site/ of the repository is generated and skipped; a checkout that lives under a directory named site is not.
    moved = tmp_path / "site" / "rialto-spec"
    moved.parent.mkdir()
    repo.rename(moved)
    (moved / "docs" / "links.md").write_text("[gone](missing.md)\n")
    assert_fails(moved, "docs/links.md: broken link missing.md")


def test_generated_site_is_skipped(repo):
    (repo / "site").mkdir()
    (repo / "site" / "page.md").write_text("[gone](missing.md) a binding\n")
    assert check(repo)[0] == 0


# 7. Schema validation ----------------------------------------------------------------------------------------


def test_valid_test_contract_against_the_schema(repo):
    (repo / "examples" / "contracts" / "valid" / "minimal.yaml").write_text(
        'rialto: "1.0.0"\ninfo: {name: minimal, version: 1.0.0}\nentities: {}\n')
    assert_fails(repo, "valid/minimal.yaml: /: 'entities' does not match any of the regexes")


def test_yaml_blocks_in_the_markdown(repo):
    (repo / "docs" / "blocks.md").write_text(
        "# Blocks\n\n"
        "```yaml\ninfo: {name: x}\n```\n\n"                               # a contract: info without version
        "```yaml\ntypes:\n  Size: {kind: nope}\n```\n\n"                  # a fragment
        "```yaml\n# rialto.lock\nanything: 1\n```\n\n"                    # skipped
        "```yaml\ninclude: [parts/*.yaml]\n```\n\n"                       # a root, skipped
        "```yaml\nnot: [a, contract]\n```\n\n"                            # not contract sections, skipped
        "```yaml\n- a list\n```\n\n"                                      # not a mapping, skipped
        "```yaml\ntypes:\n  Size: {kind: enum, members: [s]}\nx-tool: {}\n```\n")  # a valid fragment
    out = assert_fails(repo, "docs/blocks.md: line 3: yaml block /info: 'version' is a required property",
                       "docs/blocks.md: line 7: yaml block /types/Size")
    lines = {line.split(": yaml block")[0] for line in out.splitlines() if line.startswith("docs/blocks.md")}
    assert lines == {"docs/blocks.md: line 3", "docs/blocks.md: line 7"}


# 8. Contract over several files ------------------------------------------------------------------------------


FRAGMENTS = ("examples", "contracts", "valid", "fragments")


def test_valid_contract_over_several_files_that_does_not_bundle(repo):
    edit(repo.joinpath(*FRAGMENTS, "contract.rialto.yaml"), "parts/*.rialto.yaml", "nothing/*.yaml")
    assert_fails(repo, "fragments/contract.rialto.yaml: RIALTO-K007: include 'nothing/*.yaml' matches no file")


def test_bundled_contract_and_fragments_against_the_schema(repo):
    edit(repo.joinpath(*FRAGMENTS, "parts", "values.rialto.yaml"), "kind: enum", "kind: nope")
    edit(repo.joinpath(*FRAGMENTS, "parts", "thing.rialto.yaml"), "  Thing:", "  Thing:\n    unknown: 1", )
    assert_fails(repo, "fragments/contract.rialto.yaml: bundled /types/Size", "parts/values.rialto.yaml: /types/Size",
                 "parts/thing.rialto.yaml: /types/Thing")


@pytest.mark.parametrize("case, fragment, code", [
    ("not-a-mapping", "- a list\n", "RIALTO-K001"),
    ("version", 'rialto: "2.0.0"\n', "RIALTO-K003"),
    ("duplicate", 'rialto: "1.0.0"\ntypes:\n  Thing: {kind: enum, members: [a]}\n', "RIALTO-K005"),
    ("root-key", 'rialto: "1.0.0"\nsources: {}\n', "RIALTO-K008"),
    ("single-section", 'rialto: "1.0.0"\nauth: {}\n', "RIALTO-K009"),
])
def test_each_rejection_of_a_contract_over_several_files(repo, case, fragment, code):
    directory = repo.joinpath(*FRAGMENTS)
    (directory / "parts" / "zz.rialto.yaml").write_text(fragment)
    if case == "single-section":
        (directory / "parts" / "aa.rialto.yaml").write_text('rialto: "1.0.0"\nauth: {}\n')
    assert_fails(repo, f"fragments/contract.rialto.yaml: {code}:")


@pytest.mark.parametrize("include", ['"parts/*.rialto.yaml"', "[]"])
def test_include_that_is_not_a_list_of_paths(repo, include):
    edit(repo.joinpath(*FRAGMENTS, "contract.rialto.yaml"), "[parts/*.rialto.yaml]", include)
    assert_fails(repo, "fragments/contract.rialto.yaml: RIALTO-K002: include is not a list of at least one path")


def test_include_that_ends_in_two_stars_matches_nested_fragments(repo):
    directory = repo.joinpath(*FRAGMENTS)
    edit(directory / "contract.rialto.yaml", "[parts/*.rialto.yaml]", "[parts/**]")
    (directory / "parts" / "deeper" / "still").mkdir(parents=True)
    (directory / "parts" / "values.rialto.yaml").rename(directory / "parts" / "deeper" / "still" / "values.rialto.yaml")
    assert check(repo)[0] == 0
    # The nested fragment is read: a second Thing there is a duplicate.
    (directory / "parts" / "deeper" / "still" / "again.rialto.yaml").write_text(
        'rialto: "1.0.0"\ntypes:\n  Thing: {kind: enum, members: [a]}\n')
    assert_fails(repo, "fragments/contract.rialto.yaml: RIALTO-K005:", "'Thing' is declared twice under types")


def test_root_without_include_is_one_file(repo):
    edit(repo.joinpath(*FRAGMENTS, "contract.rialto.yaml"), "include: [parts/*.rialto.yaml]\n", "")
    status, out = check(repo)
    assert "fragments/contract.rialto.yaml" not in out, out


def test_fragments_merge_mappings_and_single_file_sections(repo):
    directory = repo.joinpath(*FRAGMENTS)
    (directory / "parts" / "rest.rialto.yaml").write_text('rialto: "1.0.0"\nmappings: []\nx-tool: {a: 1}\n')
    assert check(repo)[0] == 0


def test_empty_fragment_has_another_version(repo):
    (repo.joinpath(*FRAGMENTS, "parts", "empty.rialto.yaml")).write_text("")
    assert_fails(repo, "RIALTO-K003", "rialto None differs from the root")


def test_invalid_contract_over_several_files_with_another_code(repo):
    edit(repo / "examples" / "contracts" / "invalid" / "fragment-duplicate" / "contract.rialto.yaml",
         "RIALTO-K005", "RIALTO-K007")
    assert_fails(repo, "fragment-duplicate/contract.rialto.yaml: expected RIALTO-K007, got RIALTO-K005")


def test_invalid_contract_over_several_files_that_bundles(repo):
    directory = repo / "examples" / "contracts" / "invalid" / "fragment-duplicate"
    (directory / "parts" / "b.rialto.yaml").unlink()
    edit(directory / "contract.rialto.yaml", "# expect: RIALTO-K005\n", "")
    assert_fails(repo, "fragment-duplicate/contract.rialto.yaml: expected ?, got None")


def shipment(root, members="[small, large]"):
    directory = root / "examples" / "shipment"
    (directory / "split" / "parts").mkdir(parents=True)
    (directory / "shipment.rialto.yaml").write_text(
        'rialto: "1.0.0"\ninfo: {name: shipment, version: 1.0.0}\n'
        "types:\n  Size: {kind: enum, members: [small, large]}\n")
    (directory / "split" / "shipment.rialto.yaml").write_text(
        'rialto: "1.0.0"\ninfo: {name: shipment, version: 1.0.0}\ninclude: [parts/*.rialto.yaml]\n')
    (directory / "split" / "parts" / "size.rialto.yaml").write_text(
        f'rialto: "1.0.0"\ntypes:\n  Size: {{kind: enum, members: {members}}}\n')


def test_split_shipment_bundles_to_the_single_file(repo):
    shipment(repo)
    assert check(repo)[0] == 0


def test_split_shipment_that_differs_from_the_single_file(repo):
    shipment(repo, members="[small]")
    assert_fails(repo, "split/shipment.rialto.yaml: does not bundle to shipment.rialto.yaml (K5.1)")


def test_invalid_shipment_example(repo):
    shipment(repo)
    edit(repo / "examples" / "shipment" / "shipment.rialto.yaml", "kind: enum", "kind: nope")
    assert_fails(repo, "shipment/shipment.rialto.yaml: /types/Size")


# 9. Examples lines -------------------------------------------------------------------------------------------


def test_requirement_group_without_examples_line(repo):
    edit(repo / "spec" / "core.md", "## C2. Concepts and representations\n\nExamples: ",
         "## C2. Concepts and representations\n\nSee: ")
    assert_fails(repo, "spec/core.md: C2 has no Examples line (run tools/example_links.py)")


# 4. Capability tables, with a profile of a later slice -----------------------------------------------------------


DOMAIN = """# Domain profile

The requirements of this profile use the prefix D for domain.

## Capabilities

| Capability | Meaning | Requirements |
|---|---|---|
| `domain.entity` | Entities | D1.1 |
{rows}
## D1. Entities

Examples: none yet.

- **D1.1** A generator MUST generate an entity.
{groups}"""
# The domain requirements that spec/contract.md names.
GROUPS = "".join(
    f"\n## D{group}. Group {group}\n\nExamples: none yet.\n\n"
    + "".join(f"- **D{group}.{i}** A generator MUST do {i}.\n" for i in range(1, count + 1))
    for group, count in ((2, 6), (3, 8)))


def domain(root, rows=""):
    (root / "spec" / "profiles").mkdir()
    (root / "spec" / "profiles" / "domain.md").write_text(DOMAIN.format(rows=rows, groups=GROUPS))


@LATER_DOMAIN
def test_profile_with_a_capability_table(repo):
    domain(repo)
    status, out = check(repo)
    assert status == 0, out
    assert "D1.1" not in out


@LATER_DOMAIN
def test_profile_references_now_have_to_exist(repo):
    domain(repo)
    (repo / "docs" / "later.md").write_text("# Later\n\nSee D9.1.\n")
    assert_fails(repo, "docs/later.md: reference to unknown requirement D9.1")


@LATER_DOMAIN
def test_capability_table_errors(repo):
    domain(repo, rows="| `domain.entity` | Again | D1.1 |\n| `rest.server` | Other | C1.1 |\n")
    assert_fails(repo, "capability 'domain.entity' listed twice",
                 "capability 'rest.server' does not match 'domain.<name>'",
                 "capability 'rest.server' refers to C1.1 of another document")


@LATER_DOMAIN
def test_capability_table_missing(repo):
    domain(repo)
    edit(repo / "spec" / "profiles" / "domain.md", "## Capabilities", "## Abilities")
    assert_fails(repo, "spec/profiles/domain.md: Capabilities table missing")


# 10-11. Conformance levels and the generator protocol, with spec/generators.md -----------------------------------


def ticks(names):
    return ", ".join(f"`{name}`" for name in sorted(names))


def generators(root, server=None, manifest=None, examples=None, sample=None, schema_id=None):
    """spec/generators.md, its protocol schemas and tools/sample_generator.py, consistent with tools/conformance.py."""
    server = conformance.STARTER_SERVER if server is None else server
    client_added = conformance.CLIENT_STRATEGIES - conformance.STARTER_STRATEGIES
    backend_added = conformance.BACKEND_STRATEGIES - conformance.CLIENT_STRATEGIES
    manifest = manifest or {"id": "sample", "profiles": ["domain", "mapping", "rest", "errors"],
                            "capabilities": ["domain.entity"]}
    examples = examples or [manifest, {"contract": {}}, {"files": []}]
    blocks = "\n".join(f"```json\n{json.dumps(example)}\n```\n" for example in examples)
    (root / "spec" / "generators.md").write_text(f"""# Generators

## Conformance levels

| Level | Side | Capabilities and strategies |
|---|---|---|
| **Starter** | server | {ticks(server)}, {ticks(conformance.STARTER_STRATEGIES)} |
| **Starter** | client | {ticks(conformance.STARTER_CLIENT)}, {ticks(conformance.STARTER_STRATEGIES)} |
| **Backend** | | Starter (server), plus {ticks(conformance.BACKEND - conformance.STARTER_SERVER)} |
| **Client** | | Starter (client), plus {ticks(conformance.CLIENT - conformance.STARTER_CLIENT)} |

A level includes the strategies of its row; Backend and Client add {ticks(client_added)}, and Backend also {ticks(backend_added)}. That is all.

## Generator protocol

{blocks}
## After
""")
    for name, required in (("manifest", "id"), ("request", "contract"), ("response", "files")):
        (root / "spec" / f"generator-{name}-1.schema.json").write_text(json.dumps({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": schema_id or f"https://rialto.buijs.dev/spec/generator-{name}-1.schema.json",
            "type": "object", "required": [required]}))
    sample = sample or {"id": "sample", "profiles": sorted({c.split(".")[0] for c in conformance.STARTER_SERVER}),
                        "capabilities": sorted(conformance.STARTER_SERVER),
                        "strategies": sorted(s.split(": ")[1] for s in conformance.STARTER_STRATEGIES),
                        "sides": ["server"]}
    (root / "tools" / "sample_generator.py").write_text(f"MANIFEST = {sample!r}\n")


@LATER_GENERATORS
def test_conformance_levels_and_protocol(repo):
    generators(repo)
    status, out = check(repo)
    assert status == 0, out
    assert "not there yet" not in out


@LATER_GENERATORS
def test_conformance_level_differs_from_the_tool(repo):
    generators(repo, server=conformance.STARTER_SERVER - {"rest.server"} | {"rest.extra"})
    assert_fails(repo, "spec/generators.md: Starter server differs from tools/conformance.py in rest.extra, rest.server")


@LATER_GENERATORS
def test_conformance_level_rows_differ_from_the_tool(repo):
    generators(repo)
    edit(repo / "spec" / "generators.md", "| **Client** |", "| **Frontend** |")
    assert_fails(repo, "Conformance levels table has rows ['Backend', 'Frontend', 'Starter client', 'Starter server']")


@LATER_GENERATORS
def test_conformance_level_row_relative_to_the_row_above(repo):
    generators(repo)
    edit(repo / "spec" / "generators.md", "| **Client** | | Starter (client), plus",
         "| **Client** | | the same, with `presentation.list` instead of `rest.server`; also")
    assert_fails(repo, "Client differs from tools/conformance.py in")


@LATER_GENERATORS
def test_protocol_schema_missing_or_with_another_id(repo):
    generators(repo, schema_id="https://example.com/other.json")
    (repo / "spec" / "generator-response-1.schema.json").unlink()
    assert_fails(repo, "generator-response-1.schema.json missing",
                 "generator-manifest-1.schema.json: $id does not end with /spec/generator-manifest-1.schema.json")


@LATER_GENERATORS
def test_protocol_examples_of_the_wrong_kinds(repo):
    generators(repo, examples=[{"id": "a"}, {"other": 1}])
    assert_fails(repo, "Generator protocol: expected one manifest, request and response example, got ['manifest', None]")


@LATER_GENERATORS
def test_protocol_example_against_its_schema(repo):
    manifest = {"id": 1, "profiles": [], "capabilities": []}
    generators(repo, manifest=manifest, examples=[manifest, {"contract": {}}, {"files": []}])
    edit(repo / "spec" / "generator-manifest-1.schema.json", '"type": "object"',
         '"type": "object", "properties": {"id": {"type": "string"}}')
    assert_fails(repo, "spec/generators.md: manifest example /id: 1 is not of type 'string'")


@LATER_GENERATORS
def test_manifest_lists_a_capability_without_its_profile(repo):
    manifest = {"id": "sample", "profiles": ["rest"], "capabilities": ["domain.entity"]}
    generators(repo, manifest=manifest)
    assert_fails(repo, "spec/generators.md: manifest lists the capability 'domain.entity' but not its profile (C9.5)")


@LATER_GENERATORS
def test_sample_generator_that_is_not_starter_server(repo):
    generators(repo, sample={"profiles": ["rest"], "capabilities": ["rest.server"], "strategies": [],
                             "sides": ["server"]})
    assert_fails(repo, "tools/sample_generator.py: manifest /: 'id' is a required property",
                 "tools/sample_generator.py: does not declare Starter (server)")
