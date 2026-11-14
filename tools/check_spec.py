#!/usr/bin/env python3
"""Consistency checks for the Rialto specification.

1. Requirements: identifiers are unique and use their document's prefix.
2. Key words: no lowercase or mixed-case BCP 14 key words inside requirements.
3. References: every requirement identifier mentioned anywhere exists.
4. Capability tables: identifiers use the profile prefix and refer only to
   requirements of that profile.
5. Terminology: no bare "binding" (write field, operation or protocol binding),
   and no references to specific runtime libraries or earlier projects.
6. Links: every relative link and anchor resolves.
7. Examples: the Shipment contract, the valid test contracts and every contract or fragment
   snippet in the Markdown are valid against the JSON Schema (when pyyaml and jsonschema are installed).
8. Contract over several files (K5): the split Shipment bundles to shipment.rialto.yaml, every
   fragment is valid against $defs/fragment, and each invalid test directory fails with the
   code it expects.
9. Learning by example: every requirement group has an `Examples:` line (tools/example_links.py
   writes it; a group that needs none names the reason there).
10. Conformance levels: the sets in tools/conformance.py equal the table in generators.md.
11. Generator protocol: the manifest, request and response schemas are valid JSON Schemas (draft 2020-12) with
    their file name in `$id`, the JSON examples in generators.md are valid against them, the manifests list the
    profile of every capability (C9.5), and tools/sample_generator.py declares Starter (server).

The specification is built in slices: each check covers the documents and examples that exist. A reference to a
requirement of a document that does not exist yet (a profile of a later slice) is accepted; one to a missing
requirement of an existing document is an error.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec"

REQUIREMENT_DOCS = {
    "C": SPEC / "core.md",
    "K": SPEC / "contract.md",
    "D": SPEC / "profiles" / "domain.md",
    "R": SPEC / "profiles" / "rest.md",
    "M": SPEC / "profiles" / "mapping.md",
    "P": SPEC / "profiles" / "persistence.md",
    "U": SPEC / "profiles" / "presentation.md",
    "Q": SPEC / "profiles" / "query.md",
    "E": SPEC / "profiles" / "errors.md",
    "L": SPEC / "profiles" / "lifecycle.md",
    "V": SPEC / "profiles" / "versioning.md",
    "A": SPEC / "profiles" / "events.md",
    "S": SPEC / "profiles" / "auth.md",
}
# The documents of later slices are not there yet; the checks cover the ones that exist.
PENDING_PREFIXES = {prefix for prefix, path in REQUIREMENT_DOCS.items() if not path.exists()}
REQUIREMENT_DOCS = {prefix: path for prefix, path in REQUIREMENT_DOCS.items() if path.exists()}
CAPABILITY_PREFIX = {"D": "domain", "R": "rest", "M": "mapping", "P": "persistence", "U": "presentation", "Q": "query", "E": "errors", "L": "lifecycle", "V": "versioning", "A": "events", "S": "auth"}

REQ_ID = r"[ACKDELMPQRSUV]\d+\.\d+[a-z]?"
REQ_LINE = re.compile(r"^- \*\*(" + REQ_ID + r")\*\* (.*)$", re.M)
REQ_REF = re.compile(r"(?<![\w.#-])(" + REQ_ID + r")(?![\w])")
BCP14_LOWER = re.compile(r"\b(must|shall|should|may)\b")
BCP14_MIXED = re.compile(r"\b((?:MUST|SHALL|SHOULD) not)\b")
BARE_BINDING = re.compile(r"\b(\w+)\s+(bindings?)\b|\b(bindings?)\b", re.I)
FORBIDDEN = re.compile(r"\b(Fabrio|StrataStaX)\b", re.I)
LINK = re.compile(r"\]\(([^)\s]+)\)")

errors = []


def error(path, message):
    errors.append(f"{path.relative_to(ROOT)}: {message}")


def strip_code(text):
    """Remove fenced and inline code so lint rules ignore code samples."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def table_after(text, heading):
    """Return the rows (as lists of cells) of the first table after a heading."""
    index = text.find(heading)
    if index < 0:
        return None
    rows, started = [], False
    for line in text[index:].splitlines()[1:]:
        if line.startswith("|"):
            started = True
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif started or line.startswith("#"):
            break
    return rows[2:]


# 1-2. Requirements ---------------------------------------------------------------

requirements = {}

for prefix, path in REQUIREMENT_DOCS.items():
    by_group = {}
    for rid, body in REQ_LINE.findall(path.read_text()):
        if not rid.startswith(prefix):
            error(path, f"{rid}: identifier does not use prefix {prefix}")
        if rid in requirements:
            error(path, f"{rid}: duplicate identifier")
        requirements[rid] = prefix
        group, _, num = rid.partition(".")
        by_group.setdefault(group, []).append(rid)
        prose = strip_code(body)
        for word in BCP14_LOWER.findall(prose):
            error(path, f"{rid}: lowercase key word '{word}'")
        for word in BCP14_MIXED.findall(prose):
            error(path, f"{rid}: mixed-case key word '{word}', write it in capitals")
    for group, rids in by_group.items():
        expected_rids = [f"{group}.{i}" for i in range(1, len(rids) + 1)]
        if rids != expected_rids:
            error(path, f"{group}: expected sequential identifiers {expected_rids}, got {rids}")


# 2b. Standard diagnostic codes ----------------------------------------------------

DIAG_PATH = SPEC / "contract.md"
diag_rows = table_after(DIAG_PATH.read_text(), "## Standard diagnostic codes")
diagnostic_codes = set()
if diag_rows is None:
    error(DIAG_PATH, "Standard diagnostic codes table missing")
else:
    for row in diag_rows:
        code = row[0].strip("`")
        if not re.fullmatch(r"RIALTO-[KSP]\d{3}", code):
            error(DIAG_PATH, f"invalid diagnostic code '{code}'")
        if code in diagnostic_codes:
            error(DIAG_PATH, f"duplicate diagnostic code '{code}'")
        diagnostic_codes.add(code)

for invalid_file in sorted(
    list((ROOT / "examples" / "contracts" / "invalid").glob("*.yaml"))
    + list((ROOT / "examples" / "contracts" / "invalid").glob("*/contract.rialto.yaml"))
):
    expected = re.match(r"# expect: (\S+)", invalid_file.read_text())
    if not expected:
        error(invalid_file, "missing '# expect: RIALTO-...' on first line")
    elif expected.group(1) not in diagnostic_codes:
        error(invalid_file, f"expects undocumented diagnostic code '{expected.group(1)}'")


# 4. Capability tables --------------------------------------------------------------

for prefix, profile in CAPABILITY_PREFIX.items():
    if prefix not in REQUIREMENT_DOCS:
        continue
    path = REQUIREMENT_DOCS[prefix]
    rows = table_after(path.read_text(), "## Capabilities")
    if rows is None:
        error(path, "Capabilities table missing")
        continue
    seen = set()
    for row in rows:
        ident = row[0].strip("`")
        if not re.fullmatch(profile + r"\.[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*", ident):
            error(path, f"capability '{ident}' does not match '{profile}.<name>'")
        if ident in seen:
            error(path, f"capability '{ident}' listed twice")
        seen.add(ident)
        for r in REQ_REF.findall(row[-1]):
            if not r.startswith(prefix):
                error(path, f"capability '{ident}' refers to {r} of another document")


# 3, 5, 6. References, terminology and links --------------------------------------


def slug(heading):
    heading = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return heading.replace(" ", "-")


def anchors(path):
    return {slug(h) for h in re.findall(r"^#+ (.*)$", path.read_text(), re.M)}


for path in sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts and ".idea" not in p.parts and "site" not in p.parts):
    text = path.read_text()
    prose = re.sub(r"\]\([^)]*\)", "]", strip_code(text))
    prose = re.sub(r'"bindings?"', "", prose, flags=re.I)  # the word itself, quoted
    for rid in sorted(set(REQ_REF.findall(prose))):
        if rid not in requirements and rid[0] not in PENDING_PREFIXES:
            error(path, f"reference to unknown requirement {rid}")
    for match in BARE_BINDING.finditer(prose):
        if match.group(3) or match.group(1).lower() not in {"operation", "field", "protocol"}:
            line = prose[: match.start()].count("\n") + 1
            error(path, f"line {line}: '{match.group(2) or match.group(3)}' without operation, field or protocol")
    if path.parts[len(ROOT.parts):][0] == "spec":
        for match in FORBIDDEN.finditer(text):
            error(path, f"mentions '{match.group(1)}'")
    for target in LINK.findall(text):
        if re.match(r"^[a-z]+:", target):
            continue
        file_part, _, anchor = target.partition("#")
        dest = (path.parent / file_part).resolve() if file_part else path
        if not dest.exists():
            error(path, f"broken link {target}")
        elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
            error(path, f"broken anchor {target}")


# 7. Example contract --------------------------------------------------------------

SCHEMA = SPEC / "contract-1.0.0.schema.json"
EXAMPLE = ROOT / "examples" / "shipment" / "shipment.rialto.yaml"
try:
    import json
    import yaml
    import jsonschema
except ImportError:
    print("note: install pyyaml and jsonschema to validate the example contract")
else:
    schema = json.loads(SCHEMA.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    for e in validator.iter_errors(yaml.safe_load(EXAMPLE.read_text())) if EXAMPLE.exists() else []:
        error(EXAMPLE, f"/{'/'.join(map(str, e.path))}: {e.message}")
    for valid in sorted((ROOT / "examples" / "contracts" / "valid").glob("*.yaml")):
        for e in validator.iter_errors(yaml.safe_load(valid.read_text())):
            error(valid, f"/{'/'.join(map(str, e.path))}: {e.message}")
    # YAML blocks in the Markdown: a block whose keys are contract sections is checked as a contract
    # (with `info`, `sources` or both) or as a fragment (with sections only). A block that starts with
    # `# rialto.lock`, or a root with `include`, is not a contract and is skipped.
    SECTIONS = set(schema["properties"])
    block_fragment = jsonschema.Draft202012Validator(
        {"$defs": schema["$defs"], "properties": schema["properties"], "$ref": "#/$defs/fragment"}
    )
    markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), *sorted(SPEC.rglob("*.md")),
                      *sorted((ROOT / "examples").rglob("*.md"))]
    for md_path in markdown_files:
        text = md_path.read_text()
        for match in re.finditer(r"```yaml\n(.*?)```", text, flags=re.S):
            block = match.group(1)
            line = text[: match.start()].count("\n") + 1
            if block.startswith("# rialto.lock"):
                continue
            doc = yaml.safe_load(block)
            if not isinstance(doc, dict) or "include" in doc:
                continue
            if not all(key in SECTIONS or key.startswith("x-") for key in doc):
                continue
            doc = {"rialto": "1.0.0", **doc}
            if "info" in doc or "sources" in doc:
                doc.setdefault("info", {"name": "snippet", "version": "1.0.0"})
                block_validator = validator
            else:
                block_validator = block_fragment
            for e in block_validator.iter_errors(doc):
                error(md_path, f"line {line}: yaml block /{'/'.join(map(str, e.path))}: {e.message}")


    # 8. Contract over several files -------------------------------------------------

    KEYED = ["types", "shapes", "operations", "events", "subscriptions", "streams", "storage", "views"]
    ROOT_ONLY = ["info", "sources", "include"]

    class Rejected(Exception):
        """A contract over several files that K5 rejects, with the code Rialto tooling reports."""

        def __init__(self, code, message):
            super().__init__(message)
            self.code = code

    def bundle(root_file):
        """The bundled form of a contract over several files (K5), and the fragments it read."""
        root = yaml.safe_load(root_file.read_text())
        base = root_file.parent
        files = set()
        for pattern in root.pop("include", []):
            matched = {path for path in base.glob(pattern) if path.is_file() and path != root_file}
            if not matched:
                raise Rejected("RIALTO-K007", f"include '{pattern}' matches no file")
            files |= matched
        fragments = sorted(files, key=lambda path: path.relative_to(base).as_posix())
        owner = {key: root_file for key in root if key not in KEYED}
        for fragment_file in fragments:
            fragment = yaml.safe_load(fragment_file.read_text()) or {}
            if not isinstance(fragment, dict):
                raise Rejected("RIALTO-K001", f"{fragment_file}: the fragment is not a mapping")
            if fragment.get("rialto") != root.get("rialto"):
                raise Rejected("RIALTO-K003", f"{fragment_file}: rialto {fragment.get('rialto')!r} differs from the root")
            for key, value in fragment.items():
                if key == "rialto":
                    continue
                if key in ROOT_ONLY:
                    raise Rejected("RIALTO-K008", f"{fragment_file}: '{key}' belongs in the root")
                if key in KEYED:
                    section = root.setdefault(key, {})
                    for name, element in value.items():
                        if name in section:
                            raise Rejected("RIALTO-K005", f"{fragment_file}: '{name}' is declared twice under {key}")
                        section[name] = element
                elif key == "mappings":
                    root.setdefault("mappings", []).extend(value)
                elif key in owner:
                    raise Rejected("RIALTO-K009", f"{fragment_file}: '{key}' is also declared in {owner[key]}")
                else:
                    owner[key] = fragment_file
                    root[key] = value
        return root, fragments

    def resolved_sources(contract, base):
        """The contract with source paths resolved, so contracts in different directories compare."""
        sources = {name: dict(source, path=str((base / source["path"]).resolve()))
                   for name, source in contract.get("sources", {}).items()}
        return dict(contract, sources=sources)

    fragment_validator = jsonschema.Draft202012Validator(
        {"$defs": schema["$defs"], "properties": schema["properties"], "$ref": "#/$defs/fragment"}
    )
    SPLIT = ROOT / "examples" / "shipment" / "split" / "shipment.rialto.yaml"
    roots = [SPLIT] * SPLIT.exists() + sorted((ROOT / "examples" / "contracts" / "valid").glob("*/contract.rialto.yaml"))
    for root_file in roots:
        try:
            bundled, fragments = bundle(root_file)
        except Rejected as rejected:
            error(root_file, f"{rejected.code}: {rejected}")
            continue
        for e in validator.iter_errors(bundled):
            error(root_file, f"bundled /{'/'.join(map(str, e.path))}: {e.message}")
        for fragment_file in fragments:
            for e in fragment_validator.iter_errors(yaml.safe_load(fragment_file.read_text())):
                error(fragment_file, f"/{'/'.join(map(str, e.path))}: {e.message}")
        if root_file == SPLIT and resolved_sources(bundled, SPLIT.parent) != resolved_sources(
            yaml.safe_load(EXAMPLE.read_text()), EXAMPLE.parent
        ):
            error(SPLIT, f"does not bundle to {EXAMPLE.name} (K5.1)")

    for root_file in sorted((ROOT / "examples" / "contracts" / "invalid").glob("*/contract.rialto.yaml")):
        expected = re.match(r"# expect: (\S+)", root_file.read_text())
        try:
            bundle(root_file)
            code = None
        except Rejected as rejected:
            code = rejected.code
        if not expected or code != expected.group(1):
            error(root_file, f"expected {expected.group(1) if expected else '?'}, got {code}")


# 9. Every requirement group has an example ------------------------------------------

for prefix, path in REQUIREMENT_DOCS.items():
    lines = path.read_text().splitlines()
    for index, line in enumerate(lines):
        heading = re.match(r"^##+ (" + prefix + r"\d+)\. ", line)
        if heading and not any(l.startswith("Examples: ") for l in lines[index + 1:index + 4]):
            error(path.relative_to(ROOT), f"{heading.group(1)} has no Examples line (run tools/example_links.py)")


# 10. Conformance levels ---------------------------------------------------------------

def table_levels(path):
    """The levels of the Conformance levels table: per level (with the side for Starter) its capabilities and its
    strategies (`identify: member`). A row starts from another level ("Starter (server), plus …") or from the row
    above ("the same, with `a` instead of `b`"); the paragraph after the table names the strategies Backend and
    Client add."""
    section = path.read_text().split("## Conformance levels", 1)[1].split("\n## ", 1)[0].splitlines()
    capability = re.compile(r"`([a-z0-9.-]+)`")
    strategy = re.compile(r"`([a-z]+: [a-z0-9-]+)`")
    # "…; Backend and Client add `a`, `b` and `c`, and Backend also `d`. …": the strategies each level adds.
    paragraph = next(line for line in section if line.startswith("A level includes the strategies"))
    added = {}
    for part in paragraph.split(";", 1)[1].split(". ", 1)[0].split(", and "):
        names = re.split(r" (?:add|also) ", part.strip(), maxsplit=1)[0]
        for level in names.split(" and "):
            added.setdefault(level.strip(), set()).update(strategy.findall(part))
    levels = {}
    for row in (line for line in section if line.startswith("| **")):
        cells = [cell.strip() for cell in row.split("|")]
        level = cells[1].strip("*")
        name = f"{level} {cells[2]}" if level == "Starter" else level
        text = cells[3]
        if "instead of" in text:
            with_, instead = text.split("instead of")
            base, strategies = list(levels.values())[-1]
            levels[name] = (base - set(capability.findall(instead)) | set(capability.findall(with_)), strategies)
        elif text.startswith("Starter ("):
            base, strategies = levels["Starter " + text[text.index("(") + 1:text.index(")")]]
            levels[name] = (base | set(capability.findall(text)), strategies | added.get(name, set()))
        else:
            levels[name] = (set(capability.findall(text)), set(strategy.findall(text)))
    return levels


sys.path.insert(0, str(ROOT / "tools"))
import conformance  # noqa: E402

GENERATORS = SPEC / "generators.md"
expected_levels = {
    "Starter server": (conformance.STARTER_SERVER, conformance.STARTER_STRATEGIES),
    "Starter client": (conformance.STARTER_CLIENT, conformance.STARTER_STRATEGIES),
    "Backend": (conformance.BACKEND, conformance.BACKEND_STRATEGIES),
    "Client": (conformance.CLIENT, conformance.CLIENT_STRATEGIES),
}
if not GENERATORS.exists():
    print("note: spec/generators.md is not there yet; conformance levels and generator protocol not checked")
else:
    found_levels = table_levels(GENERATORS)
    if set(found_levels) != set(expected_levels):
        error(GENERATORS, f"Conformance levels table has rows {sorted(found_levels)}, tools/conformance.py {sorted(expected_levels)}")
    for name, (capabilities, strategies) in expected_levels.items():
        if name in found_levels and found_levels[name] != (capabilities, strategies):
            table_capabilities, table_strategies = found_levels[name]
            difference = sorted(table_capabilities ^ capabilities) + sorted(table_strategies ^ strategies)
            error(GENERATORS, f"{name} differs from tools/conformance.py in {', '.join(difference)}")


    # 11. Generator protocol ---------------------------------------------------------------

    PROTOCOL_SCHEMAS = {name: SPEC / f"generator-{name}-1.schema.json" for name in ("manifest", "request", "response")}
    try:
        import json
        import jsonschema
    except ImportError:
        print("note: install jsonschema to check the generator protocol schemas")
    else:
        protocol_validators = {}
        for name, path in PROTOCOL_SCHEMAS.items():
            if not path.exists():
                error(GENERATORS, f"{path.name} missing")
                continue
            protocol_schema = json.loads(path.read_text())
            jsonschema.Draft202012Validator.check_schema(protocol_schema)
            if not protocol_schema.get("$id", "").endswith(f"/spec/{path.name}"):
                error(path, f"$id does not end with /spec/{path.name}")
            protocol_validators[name] = jsonschema.Draft202012Validator(protocol_schema)
        protocol_text = GENERATORS.read_text().split("## Generator protocol", 1)[-1].split("\n## ", 1)[0]
        examples = [json.loads(block) for block in re.findall(r"```json\n(.*?)```", protocol_text, flags=re.S)]
        # An example is a manifest (with `id`), a request (with `contract`) or a response (with `files`).
        kinds = [next((k for k, key in (("manifest", "id"), ("request", "contract"), ("response", "files")) if key in e), None)
                 for e in examples]
        if sorted(filter(None, kinds)) != ["manifest", "request", "response"] or None in kinds:
            error(GENERATORS, f"Generator protocol: expected one manifest, request and response example, got {kinds}")
        for kind, example in zip(kinds, examples):
            if kind in protocol_validators:
                for e in protocol_validators[kind].iter_errors(example):
                    error(GENERATORS, f"{kind} example /{'/'.join(map(str, e.absolute_path))}: {e.message}")
        import sample_generator  # noqa: E402

        # C9.5: the profile of every capability is among the profiles of a manifest.
        for where, manifest in [(GENERATORS, e) for k, e in zip(kinds, examples) if k == "manifest"] + [
                (ROOT / "tools" / "sample_generator.py", sample_generator.MANIFEST)]:
            for capability in manifest.get("capabilities", []):
                if capability.split(".")[0] not in manifest.get("profiles", []):
                    error(where, f"manifest lists the capability '{capability}' but not its profile (C9.5)")

        if "manifest" in protocol_validators:
            for e in protocol_validators["manifest"].iter_errors(sample_generator.MANIFEST):
                error(ROOT / "tools" / "sample_generator.py", f"manifest /{'/'.join(map(str, e.absolute_path))}: {e.message}")
        starter_strategies = {strategy.split(": ")[1] for strategy in conformance.STARTER_STRATEGIES}
        if (set(sample_generator.MANIFEST["capabilities"]) != conformance.STARTER_SERVER
                or set(sample_generator.MANIFEST["strategies"]) != starter_strategies
                or sample_generator.MANIFEST["sides"] != ["server"]):
            error(ROOT / "tools" / "sample_generator.py", "does not declare Starter (server) as tools/conformance.py has it")


# Report -----------------------------------------------------------------------------

if errors:
    print("\n".join(errors))
    print(f"\n{len(errors)} error(s); {len(requirements)} requirements.")
    sys.exit(1)
print(f"OK: {len(requirements)} requirements, all checks passed.")
