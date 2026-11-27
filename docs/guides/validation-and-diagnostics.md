# Validation and diagnostics

A tool reads a contract before anything is built from it, and reports what is wrong in a form people and tools can act
on. This guide explains which layers of a contract a tool checks, what it reports for each mistake, and why every tool
reports the same code. It is for contract authors and for builders of Rialto tooling. It is informative: the rules are
those of [C5](../../spec/core.md#c5-validation-configuration-and-diagnostics), [K1](../../spec/contract.md#k1-document)
and the [standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes), and this guide cites them rather
than repeating them.

## Why

A contract is the input of many tools: validators, build plugins and generators, in different languages. They must
agree on whether a contract is valid, and on why it is not.

- **The same verdict everywhere.** The structure of a contract is defined by a JSON Schema, and every language has a
  JSON Schema validator. So every tool rejects a malformed contract in the same way (K1.7).
- **The same reason everywhere.** Each kind of mistake has one standard code, such as `RIALTO-K004` for a reference
  that does not resolve (K1.10). Shared test contracts and tooling in several languages only agree on why a contract
  failed when they report the same code for the same violation.
- **Actionable findings.** A [diagnostic](../../spec/core.md#terminology) is actionable when it names the input
  location, the rule involved, and whether the run failed (C5.1, C5.12). An author can then go straight to the line
  and fix it.

## How it works

A tool checks a contract at several layers:

| Layer | What is checked | Codes |
|---|---|---|
| The document | One YAML or JSON document, a mapping at the top, and in YAML only what JSON can express (K1.11) | `RIALTO-K001` |
| The format version | The `rialto` version is one the tool supports (K1.1, C5.7) | `RIALTO-K003` |
| The JSON Schema | The structure: known keys, value types, required keys (K1.7, C5.8) | `RIALTO-K002` |
| The format rules | References, names and type expressions, which the schema cannot see (K1.2, K1.3, K2.1) | `RIALTO-K004` to `RIALTO-K006` |
| The sources | Declared source files and references into them (K1.2, K1.9) | `RIALTO-S001`, `RIALTO-S002` |
| The profiles | The rules of each profile | `RIALTO-P001` and up |

A contract over several files adds its own checks while its files are read
([contracts over several files](contracts-over-several-files.md), `RIALTO-K007` to `RIALTO-K009`), and a remote source adds
those of the lock ([remote sources](remote-sources.md), `RIALTO-K010`, `RIALTO-S003` to `RIALTO-S005`).

- **The version comes first.** The JSON Schema belongs to a format version (K1.7), so a contract of another version is
  not judged by this schema.
- **The schema checks structure only.** References, names and the form of a type expression are checked by the tool
  itself (K1.7).
- **Every finding has a code, a severity and a location.** The code is the one the
  [table](../../spec/contract.md#standard-diagnostic-codes) lists for the violated rule (K1.10). The severity tells an
  error from a warning (C5.11). The location is the file and the place in it (C5.1); for a contract over several files,
  the fragment (K5.5).
- **A run with an error fails.** A tool never reports it as successful (C5.12).

For example, the test contract
[`invalid/unknown-type.yaml`](../../examples/contracts/invalid/unknown-type.yaml) refers to a type `Person` that it does
not declare:

```yaml
# expect: RIALTO-K004
# capabilities: domain.entity
rialto: "1.0.0"
info: {name: unknown-type, version: 1.0.0}
types:
  Thing:
    kind: entity
    identity: [id]
    properties:
      id: {type: uuid}
      owner: {type: Person}
```

The reference tooling reports it with `rialto validate` as:

```text
error[RIALTO-K004] unknown-type.yaml:11:15 #/types/Thing/properties/owner/type: Unknown type 'Person' (K1.2)
```

That line has the severity, the code, the file, line and column, a JSON Pointer to the element, the message and the
requirement. Each tool documents how it reports its findings (C5.12). For editors and CI annotations, the specification
recommends one JSON document with the same fields; it is
[informative](../../spec/contract.md#standard-diagnostic-codes), not a requirement:

```json
{
  "severity": "error", "code": "RIALTO-K004", "requirement": "K1.2",
  "file": "unknown-type.yaml", "line": 11, "column": 15,
  "pointer": "/types/Thing/properties/owner/type",
  "message": "Unknown type 'Person'", "hint": null
}
```

`line`, `column`, `requirement` and `hint` are null when unknown.

## Scenarios

### What is wrong with a contract

| Situation | Code | Test contract |
|---|---|---|
| A file that is not valid YAML or JSON | `RIALTO-K001` | — |
| A document that is a list, not a mapping | `RIALTO-K001` | [`not-a-mapping.yaml`](../../examples/contracts/invalid/not-a-mapping.yaml) |
| An unsupported `rialto` version, such as `"0.2"` | `RIALTO-K003` | [`unsupported-version.yaml`](../../examples/contracts/invalid/unsupported-version.yaml) |
| An unknown key, such as `entities` at the top | `RIALTO-K002` | [`unknown-key.yaml`](../../examples/contracts/invalid/unknown-key.yaml) |
| A type that is used but not declared | `RIALTO-K004` | [`unknown-type.yaml`](../../examples/contracts/invalid/unknown-type.yaml) |
| A name that is both a type and a shape | `RIALTO-K005` | [`duplicate-name.yaml`](../../examples/contracts/invalid/duplicate-name.yaml) |
| A map key that is a value object | `RIALTO-K006` | [`map-key.yaml`](../../examples/contracts/invalid/map-key.yaml) |
| A collection of collections, such as `list<list<int32>>` | `RIALTO-K006` | [`type-expression.yaml`](../../examples/contracts/invalid/type-expression.yaml) |
| A declared source file that does not exist | `RIALTO-S001` | [`missing-source.yaml`](../../examples/contracts/invalid/missing-source.yaml) |
| A reference into a source that does not resolve | `RIALTO-S002` | [`unresolved-external.yaml`](../../examples/contracts/invalid/unresolved-external.yaml) |

Every code, with its requirement, is in the [standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes).
References and sources have their own guide, [sources and references](sources-and-references.md), and so do
[types](types.md).

### What a run reports

| Situation | What the tool does | Requirement |
|---|---|---|
| The contract has no errors | Reports success; the conformance runner expects exit status 0 | C5.12 |
| The contract has an error | Reports the error with its code; never reports success. The conformance runner expects another exit status | K1.10, C5.12 |
| The contract has a warning only | Reports it as a warning, apart from errors | C5.11 |
| The mistake is in a fragment | The diagnostic names the fragment and the place in it | K5.5 |
| The tool checks a rule of its own, such as one of generation | Uses a code of its own, with another letter, and documents it | C5.11 |
| A generator is run by a tool that has validated the contract | The generator need not validate it again | K1.7 |

## Edge cases

| Situation | What happens |
|---|---|
| A key used twice in one mapping | `RIALTO-K001` ([`duplicate-key.yaml`](../../examples/contracts/invalid/duplicate-key.yaml)). Reading on would drop one of the two without a word. |
| A second document in the same file, after `---` | `RIALTO-K001` ([`two-documents.yaml`](../../examples/contracts/invalid/two-documents.yaml)). A contract is one document. |
| A tag beyond the YAML 1.2 core schema, such as `!shipment` | `RIALTO-K001` ([`yaml-tag.yaml`](../../examples/contracts/invalid/yaml-tag.yaml), K1.11). `!!str`, `!!int` and the other core tags are allowed. |
| An anchor or an alias, such as `&info` and `*info` | `RIALTO-K001` ([`yaml-alias.yaml`](../../examples/contracts/invalid/yaml-alias.yaml), K1.11). |
| A key that is not a string, such as `1:`, `true:` or `~:` | `RIALTO-K001` ([`yaml-key.yaml`](../../examples/contracts/invalid/yaml-key.yaml), K1.11). Quote it: `"1":`. |
| A contract in JSON | Checked like one in YAML: both represent the same data model ([document](../../spec/contract.md#document)). |
| A key that starts with `x-` | No diagnostic: an extension is exempt from C5.8. A generator ignores the extensions of other generators (K1.8). |
| An integer above the maximum of the JSON Schema, such as a `maxLength` of `99999999999999` | `RIALTO-K002` ([`integer-overflow.yaml`](../../examples/contracts/invalid/integer-overflow.yaml)). |
| A contract of an older or newer format version | `RIALTO-K003`. It is not read as a supported version (C5.7). |
| A fragment of another format version than its root | `RIALTO-K003` ([`fragment-version/`](../../examples/contracts/invalid/fragment-version/), K5.3). |
| A contract with several mistakes | A test contract names the codes it must produce in its `# expect:` lines. A tool passes when it rejects the contract and names each of them; it may report more ([running the test contracts](../../examples/contracts/README.md#running-the-test-contracts)). |
| A lock that cannot be read | `RIALTO-K010`, and the other findings of the run are still reported (K4.5). See [remote sources](remote-sources.md). |

## Design decisions

From the rationale of the [contract format](../../spec/contract.md#rationale):

- **A JSON Schema, not prose only (K1.7).** Every language has a JSON Schema validator, so generators reject malformed
  contracts identically.
- **Standard diagnostic codes (K1.10).** Shared test contracts and multi-language tooling only agree on why an invalid
  contract failed when they report the same code for the same violation.
- **YAML and JSON (K1.11).** YAML is pleasant to write, JSON easy to generate and validate. Restricting YAML to the
  JSON data model keeps them equivalent. A tag or a key that is not a string has no JSON form, so a tool would have to
  drop or change it; an alias makes a document whose meaning depends on expanding it, and one that can grow
  exponentially when it is.
- **Type expressions checked by the tool, not the schema (K1.7, K2.1).** A schema pattern can only say that a type is
  wrong; the tool can say why, with `RIALTO-K006` or `RIALTO-P021` at the property, and report the other findings of
  the contract in the same run.

Following from the requirements:

- **The version before the schema (K1.1, K1.7, C5.7).** The schema a contract is checked against is the one of its
  `rialto` version. A contract of an unsupported version is rejected as such, not reinterpreted.
- **Unknown keys are schema errors (C5.8).** An unknown key is reported as `RIALTO-K002`, never ignored in favor of
  default behavior. Only extension keys (`x-`) are exempt.
- **The code names the area, not the requirement.** The letter after `RIALTO-` is the area of the check: `K` the
  contract, `S` its sources, `P` the rules of a profile. The requirement is a column of its own in the
  [table](../../spec/contract.md#standard-diagnostic-codes).

## Requirements

| Requirement | In short |
|---|---|
| [C5.1](../../spec/core.md#c5-validation-configuration-and-diagnostics) | Keep enough provenance for actionable diagnostics |
| [C5.7](../../spec/core.md#c5-validation-configuration-and-diagnostics) | Reject an unsupported version; never reinterpret it |
| [C5.8](../../spec/core.md#c5-validation-configuration-and-diagnostics) | Diagnose unknown keys; `x-` keys are exempt |
| [C5.11](../../spec/core.md#c5-validation-configuration-and-diagnostics) | Use the standard codes; document own codes and severities; tell warnings from errors |
| [C5.12](../../spec/core.md#c5-validation-configuration-and-diagnostics) | Report severity, code and provenance; never report a run with an error as successful |
| [K1.1](../../spec/contract.md#k1-document) | Reject an unsupported `rialto` version |
| [K1.2](../../spec/contract.md#k1-document) | Every reference resolves to exactly one element |
| [K1.3](../../spec/contract.md#k1-document) | Names are unique |
| [K1.7](../../spec/contract.md#k1-document) | Reject a contract that is not valid against the JSON Schema of its version |
| [K1.10](../../spec/contract.md#k1-document) | Report each rule of the table with its standard code |
| [K1.11](../../spec/contract.md#k1-document) | A YAML contract uses only what JSON can express |
| [K5.5](../../spec/contract.md#k5-contract-over-several-files) | A diagnostic in a fragment names the fragment |

C5 also covers generator configuration and generation stages (C5.2 to C5.6, C5.9, C5.10); those apply to generators.

| Code | Meaning |
|---|---|
| `RIALTO-K001` | The document is not valid YAML or JSON, is not a mapping, or uses YAML that JSON cannot express |
| `RIALTO-K002` | The contract violates the JSON Schema |
| `RIALTO-K003` | Unsupported `rialto` version |
| `RIALTO-K004` | A reference to a contract element does not resolve, or names a source the contract does not declare |
| `RIALTO-K005` | A name is declared twice |
| `RIALTO-K006` | Invalid type expression |
| `RIALTO-S001` | A declared source file cannot be read or parsed |
| `RIALTO-S002` | A reference into a source does not resolve |

All codes are in the [standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes).
