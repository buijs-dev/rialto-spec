# Contributing

## Before you open a pull request

1. Run the checks; they must report OK. They are Dart scripts and need only the [Dart SDK](https://dart.dev/get-dart):

   ```sh
   (cd tools && dart pub get)               # once
   dart run tools/bin/check_spec.dart
   dart run tools/bin/example_links.dart    # must leave the Markdown unchanged
   ```

   The checks cover the documents: identifiers, key words, references, terms, links and the `Examples:` lines. Whether
   an example is a valid contract is checked by the tooling: [rialto-jvm](https://github.com/buijs-dev/rialto-jvm)
   tests itself against the test contracts and the snippets of this repository.

   After a change to `tools/`, also run its tests:

   ```sh
   cd tools && dart test && dart analyze && dart format --output=none --set-exit-if-changed .
   ```

2. Add a line under `[Unreleased]` in the [changelog](CHANGELOG.md).

## Layout

| Path | Contents |
|---|---|
| `spec/overview.md`, `spec/contract.md`, `spec/core.md` | What applies everywhere |
| `spec/contract-1.0.0.schema.json` | JSON Schema of the contract format |
| `spec/profiles/` | One profile per layer (from slice 1, one slice per profile) |
| `spec/generators.md` | What a generator must document; generators themselves live in their own repositories (slice 10) |
| `docs/` | Tooling overview (informative) |
| `GOVERNANCE.md` | Roles, decisions, versions and conformance |
| `site/` | The site at [rialto.buijs.dev](https://rialto.buijs.dev/), built from the Markdown of this repository |
| `examples/shipment/` | The one example every document draws from (grows with the slices) |
| `examples/contracts/` | Shared test contracts every implementation must validate the same way |
| `tools/bin/check_spec.dart` | Consistency checks of the documents |
| `tools/bin/example_links.dart` | Writes the `Examples:` lines under the requirement groups |
| `tools/lib/`, `tools/test/` | The code of both scripts, and its tests |

A profile has the sections Purpose, Example, Terms, Contract, Capabilities, Requirements and Rationale, in that order. Extra sections may be added after Terms and before Capabilities.

## Requirements

Write a requirement as a list item starting with its identifier:

```markdown
- **M2.4** A generator MUST …
```

| Prefix | Document | Prefix | Document |
|---|---|---|---|
| C | core | P | persistence |
| K | contract | Q | query |
| A | events | R | REST |
| D | domain | S | auth |
| E | errors | U | presentation |
| L | lifecycle | V | versioning |
| M | mapping | | |

- Identifiers are stable. Never reuse a removed one; a split requirement gets a letter suffix.
- Key words (MUST, SHOULD, MAY, and their NOT forms) are capitals, and only inside requirements.
- An obligation on generators reads "A generator MUST document …".
- Capabilities are named `<profile>.<name>` and refer only to requirements of their own profile.
- A deliberate choice, or a rejected alternative, goes into the Rationale section of its document: one to three lines saying why.

## Writing style

- No history, no references to earlier projects or specific runtime libraries.
- Write "and" or "or" instead of a slash; use a list or table for more than three items.
- Add a MUST NOT only for a pitfall the positive rule does not already exclude.
- Use "binding" only as field binding, operation binding or protocol binding (as CloudEvents defines it).
- Implementation status and known gaps belong in the implementation's repository.
- Every requirement group shows its use: a line `Examples:` under its heading links to the Shipment scenarios and test contracts that exercise it. Run `dart run tools/bin/example_links.dart` after adding a scenario or test contract.

## What the checks cover

- Requirement identifiers: unique, correct prefix, and every reference resolves.
- Key words inside requirements: no lowercase or mixed case.
- Capability tables: naming and references.
- Terminology: "binding" and forbidden names.
- Links and anchors.
- The checks cover the documents and examples that exist; a reference to a requirement of a profile that has not arrived yet is accepted.
- With `pyyaml` and `jsonschema` installed: the Shipment contract (once it is there), `examples/contracts/valid/` and every YAML block in the Markdown whose keys are contract sections, against the JSON Schema. Start a YAML block that is not a contract, such as a lock file, with `# rialto.lock`. The `invalid/` contracts need real tooling and are not checked here, except the contracts over several files.
