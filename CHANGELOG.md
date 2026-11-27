# Changelog

All notable changes for readers of the specification and for builders of Rialto tooling are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

The first version, slice 0: the whole contract format 1.0.0 with its JSON Schema, the rules every generator follows,
and the test contracts that check a tool against them. What each section means for generated code comes with the
profile of its slice.

### Added

**Specification**

- Guides that explain a feature in depth: why it exists, what a tool does in each situation, the edge cases and the
  design decisions. [Validation and diagnostics](docs/guides/validation-and-diagnostics.md),
  [contracts over several files](docs/guides/contracts-over-several-files.md),
  [sources and references](docs/guides/sources-and-references.md),
  [remote sources and the lock](docs/guides/remote-sources.md) and [types](docs/guides/types.md).

- The [overview](spec/overview.md), [core](spec/core.md) and the [contract format](spec/contract.md). Core defines the
  terms and the rules every generator follows (C1–C8).
- Every requirement has a stable id, such as `K1.2`, so tools, tests and findings can cite it. Requirements use MUST,
  SHOULD and MAY (BCP 14).
- Every document ends with the rationale for its choices, including the alternatives that were rejected.

**Contract format 1.0.0**

- A JSON Schema for every section: [`spec/contract-1.0.0.schema.json`](spec/contract-1.0.0.schema.json), also served
  at `https://rialto.buijs.dev/spec/contract-1.0.0.schema.json`. Point your editor at it for completion and checks
  while you write a contract.
- Types (K2): every type has exactly one JSON form on the wire. Decimals, date-times, durations, map keys, extensible
  enums, discriminated unions, and `json` and `binary` for free-form and binary data.
- Every number in a contract (`maxLength`, `maxItems`, `maxSize`, …) is a 32-bit signed integer, at most 2147483647,
  so every language can hold it.
- The form of a type expression is checked by the tool, not by the JSON Schema (K1.7): an invalid one, such as
  `list<list<int32>>` or `map<boolean, string>`, is `RIALTO-K006`, and a `binary` in a collection `RIALTO-P021`.
- A YAML contract uses only what JSON can express (K1.11): keys are strings, no anchors or aliases, and no tags
  beyond the YAML 1.2 core schema; anything else is `RIALTO-K001`.
- A reference to a source the contract does not declare is `RIALTO-K004`, like any other unresolved name.
- `description` in CommonMark on types, properties, shapes, operations, events and error codes (K3).
- Sources (K4): a contract points into OpenAPI, AsyncAPI and SQL documents instead of repeating them. A SQL source can
  be the migrations of a service, applied in version order (K1.9). Remote sources are pinned by hash in the lock of the
  contract, `shipment.rialto.lock` next to `shipment.rialto.yaml`, which names the contract it belongs to, so contracts
  in one directory never share a lock (K4.6, K4.7); a lock that cannot be read or written, or belongs to another
  contract, is an error (`RIALTO-K010`), never an empty lock.
- Contracts over several files (K5): a root lists its fragments under `include`, and they merge by name into one
  bundled document.
- Extension keys `x-<generator>-<name>` for the settings of one generator (K1.8).
- Standard diagnostic codes (K1.10): `RIALTO-K…` for the format, `RIALTO-S…` for sources and `RIALTO-P…` for the rules
  of the profiles. Every tool reports the same code for the same problem. The table lists every code already; the
  `P` rules come with their profiles.

**Checking a tool**

- Test contracts in [`examples/contracts`](examples/contracts/README.md): valid contracts that must pass, and invalid
  ones that each name the codes they must produce. They cover documents that are not a mapping, a key that is used
  twice, a file with two documents, schema violations, unsupported versions, unresolved references, duplicate names,
  invalid map keys, missing sources, an unusable lock, a lock of another contract and contracts over several files.
- `rialto conformance`, of [rialto-jvm](https://github.com/buijs-dev/rialto-jvm), runs any tool over the test
  contracts and reports per contract whether it passed, so anyone can repeat a claim of conformance.
- The test contracts, the JSON Schema and the Markdown of the specification are published together as
  `dev.buijs.rialto:rialto-spec`, so a tool can test against a fixed version of them.

**Project**

- The site [rialto.buijs.dev](https://rialto.buijs.dev/), built from this repository.
- Licensed under the Apache License 2.0.
