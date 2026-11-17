# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Towards Specification 1.0.0, with contract format 1.0.0, built in slices. This section holds slice 0, the foundation.

### Added

#### Specification

- Overview, core terminology and the rules every generator follows (C1–C8).
- Requirements with stable identifiers per document (C, K, A, D, E, L, M, P, Q, R, S, U, V) and the keywords MUST, SHOULD and MAY (BCP 14).
- A rationale per document, with the alternatives that were rejected.

#### Contract format

- Contract format 1.0.0 and its JSON Schema (`spec/contract-1.0.0.schema.json`), complete for every section, with the `$id` `https://rialto.buijs.dev/spec/contract-1.0.0.schema.json`, the address where the site serves it.
- Type system: JSON representation per type, decimals, date-times, durations, map keys, extensible enums, discriminated unions and the `json` and `binary` scalars (K2).
- `description` (CommonMark) on types, properties, shapes, operations, events and error codes (K3).
- Sources: OpenAPI, AsyncAPI and SQL documents, including SQL sources over a service's migrations applied in version order (K1.9), and remote sources pinned by hash in `rialto.lock`, with `RIALTO-K010` for a lock that cannot be read or written (K4).
- A contract over several files: a root with `include` and fragments merged by name, with one bundled form (K5).
- Extension keys named after their generator, `x-<generator>-<name>` (K1.8).
- Standard diagnostic codes (`RIALTO-K*`, `RIALTO-S*`, `RIALTO-P*`) (K1.10). The table lists every code as the reference of the format; the `RIALTO-P*` checks are specified with their profiles.

#### Examples and checks

- Shared test contracts in `examples/contracts` for the contract format and core: documents that are not a mapping (`RIALTO-K001`), schema violations (`RIALTO-K002`), unsupported versions (`RIALTO-K003`), unresolved references (`RIALTO-K004`, `RIALTO-S002`), duplicate names (`RIALTO-K005`), invalid map keys (`RIALTO-K006`), missing sources (`RIALTO-S001`), a `rialto.lock` that is a directory (`RIALTO-K010`) and contracts over several files (`RIALTO-K002`, `RIALTO-K003`, `RIALTO-K005`, `RIALTO-K007` to `RIALTO-K009`), with `**` in an include path matching any number of segments.
- `tools/check_spec.py`: unique identifiers, keyword use, capability tables, terminology, links and schema validation of the test contracts and of every contract snippet in the Markdown; it checks the documents and examples that exist.
- `tools/example_links.py`: the `Examples:` line under every requirement group.
- `tools/conformance.py`: runs any tool over the shared test contracts, so a claim of conformance can be repeated by anyone; `--jobs` runs contracts in parallel for a command whose runs share nothing.
- `tools/compare_tools.py`: compares the findings of two tools over the test contracts by file, severity, code, pointer and requirement (optionally position and message), as conformance compares only codes.
- `tools/tests/`: pytest tests of the four tools, run in CI with a coverage report.

#### Project

- README, contributing guide, governance, notice and licence (Apache 2.0).
- The site at `https://rialto.buijs.dev/`, built from the Markdown of this repository, and the CI that checks the specification and deploys the site.
