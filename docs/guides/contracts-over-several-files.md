# Contracts over several files

A large contract can be written as a root and fragments. This guide explains how a tool reads such a contract, how
the files merge into one document, what a tool does when they do not fit together, and why it works this way. It is
for contract authors and for builders of Rialto tooling. It is informative: the rules are those of
[Contract over several files](../../spec/contract.md#contract-over-several-files) and
[K5](../../spec/contract.md#k5-contract-over-several-files), and this guide cites them rather than repeating them.

## Why

A large contract can be split over files for its authors. Splitting is a matter of authoring, not of meaning:
everything after reading works on one document. How a team splits its files is its own choice, while generators in
other languages, compatibility checks and published contracts keep one document as input. That gives three
properties:

- **One meaning.** A contract and its bundled form mean the same; bundling drops, changes and reorders nothing within
  a section (K5.1).
- **One exchange format.** The bundled form is what is published, compared between versions and read by generators of
  other languages ([Contract over several files](../../spec/contract.md#contract-over-several-files)).
- **Findings in the file you edit.** A diagnostic about an element of a fragment names that fragment and the place in
  it, not the bundled form (K5.5).

## How it works

```yaml
# shipment.rialto.yaml, the root
rialto: "1.0.0"
info: {name: shipment, version: 2.0.0}
sources:
  api: {kind: openapi, path: openapi.json, version: 2.0.0, status: current}
include: [contract/*.rialto.yaml]
```

```yaml
# contract/shipment.rialto.yaml, a fragment
rialto: "1.0.0"
types:
  Shipment: {kind: entity, identity: [id], properties: {id: {type: ShipmentId}}}
storage:
  Shipment: {table: db#shipment, columns: {id: public_id}}
```

```yaml
# contract/values.rialto.yaml, a fragment
rialto: "1.0.0"
types:
  ShipmentId: {kind: value, wraps: uuid}
```

- **The root** holds `rialto`, `info` and `sources`, and lists its fragments under `include`. It may hold sections
  too. Tools are given the root: `rialto validate shipment.rialto.yaml`.
- **A fragment** holds `rialto` and any of the sections, never `info`, `sources` or `include` (K5.2). Its `rialto` is
  the root's (K5.3).
- **`include`** is a list of paths relative to the root, also for one path. In a path, `*` matches any characters
  within one segment and `**` any number of segments: `contract/**` matches every file below `contract/`. Every path
  must match a file (K5.2).
- **Reading order.** The matched files are read in code point order of their path. A file that two paths match is
  read once.
- **Merge by name.** `types`, `shapes`, `operations`, `events`, `subscriptions`, `streams`, `storage` and `views`
  merge per name, and a name is declared in one file only (K5.4). In the example, `types` of the bundled form holds
  `Shipment` and `ShipmentId`.
- **Mappings** are concatenated: those of the root first, then those of the fragments in reading order.
- **Single-file sections.** `errors`, `auth`, `navigation` and top-level extension keys appear in one file only
  (K5.4).
- **Names and references across files.** `Shipment` refers to `ShipmentId` of another fragment by name. Every
  `source#location`, such as `db#shipment`, resolves against the `sources` of the root.
- **The bundled form** is the merged contract, without `include`. It is valid against the contract schema, and each
  fragment against `$defs/fragment` of that schema (K5.6). `rialto bundle --output bundled.rialto.yaml
  shipment.rialto.yaml` writes it.
- **Locations.** Validation works on the bundled form, but every finding about an element of a fragment names the
  fragment, with its line and column (K5.5). The JSON output of a validator gives that fragment as `file`
  ([standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes)).

## Scenarios

### Reading the files

| Situation | What the tool does | Diagnostic |
|---|---|---|
| Every `include` path matches files | Reads them as fragments, in code point order of their path | — |
| Two paths match the same file | Reads it once | — |
| An `include` path matches no file | Rejects it (K5.2) | `RIALTO-K007` |
| A fragment is not valid YAML or JSON, or not a mapping | Rejects it | `RIALTO-K001` |
| A fragment declares `info`, `sources` or `include` | Rejects it (K5.2) | `RIALTO-K008` |
| The `rialto` of a fragment differs from the root's | Rejects it (K5.3) | `RIALTO-K003` |
| A fragment is not valid against `$defs/fragment` | Rejects it (K5.6) | `RIALTO-K002` |

### Merging

| Situation | What the tool does | Diagnostic |
|---|---|---|
| A fragment refers to a type of another fragment | Resolves it by name | — |
| A fragment refers to `db#shipment` | Resolves it against the `sources` of the root | — |
| Two files declare the same name in one section | Rejects it (K5.4) | `RIALTO-K005` |
| The root and fragments have `mappings` | Concatenates them: the root first, then the fragments in reading order | — |
| One file declares `errors`, `auth` or `navigation` | Takes it as it is | — |
| Two files declare `errors`, `auth`, `navigation` or the same top-level extension key | Rejects it (K5.4) | `RIALTO-K009` |
| A finding of another check is about an element of a fragment | Names the fragment and the place in it (K5.5) | the finding itself |

### Bundling

| Situation | What the tool does | Diagnostic |
|---|---|---|
| A contract over several files | Writes one document: the merged sections, without `include` (K5.1) | — |
| A contract in one file, without `include` | It is its own bundled form | — |
| The bundled form | Is valid against the contract schema (K5.6) | `RIALTO-K002` when it is not |

## Edge cases

| Situation | What happens |
|---|---|
| `include: []` | `RIALTO-K002`: `include` lists at least one path. |
| `include: "contract/*.rialto.yaml"`, a string | `RIALTO-K002`: `include` is a list, also for one path. |
| The same path twice in `include` | `RIALTO-K002`: the paths of `include` are unique. |
| Two paths, one matches files and the other none | `RIALTO-K007` for the path without a match. The match of the other path does not make up for it. |
| `types` of the root is no mapping, and a fragment has `types` | `RIALTO-K002` on the root. Merging the fragment in must not hide the mistake. |
| A fragment that is a list | `RIALTO-K001`: a fragment is a mapping of sections. |
| A fragment with `rialto: "0.2"` under a root with `"1.0.0"` | `RIALTO-K003` (K5.3). |
| A fragment with `sources` | `RIALTO-K008`: every `source#location` resolves against the `sources` of the root. |
| The same type name in two fragments, also with another `kind` | `RIALTO-K005`, the same error as for a name declared twice in one file. |
| Two fragments with the same `errors`, even word for word | `RIALTO-K009`: `errors` belongs in one file. |
| `include: [parts/**]` | Matches every file below `parts/`, at any depth. A type may refer to a type two directories away. |
| The lock of a contract over several files | One lock, next to the root and named after it. Fragments have no `sources` (see [Remote sources and the lock](remote-sources.md)). |
| An SQL source over migrations | Its `path` uses the same `*` and `**` as `include` ([Sources and references](../../spec/contract.md#sources-and-references)). |

## Design decisions

From the [rationale](../../spec/contract.md#rationale) of the specification:

- **Fragments merged by name, not by `$ref` (K5).** Elements of a contract already refer to each other by name, so
  files merge without an index of pointers, and a duplicate is the same error as in one file. JSON `$ref` would need
  such an index, and the bundlers built for OpenAPI do not read other kinds of documents.
- **One bundled form (K5.1).** How a team splits its files is its own choice; generators in other languages,
  compatibility checks and published contracts keep one document as input.

## Requirements

| Requirement | In short |
|---|---|
| [K5.1](../../spec/contract.md#k5-contract-over-several-files) | A contract and its bundled form have the same meaning; bundling drops, changes or reorders nothing within a section |
| [K5.2](../../spec/contract.md#k5-contract-over-several-files) | Reject an `include` path without a match, and a fragment with `info`, `sources` or `include` |
| [K5.3](../../spec/contract.md#k5-contract-over-several-files) | Reject a fragment whose `rialto` version differs from the root's |
| [K5.4](../../spec/contract.md#k5-contract-over-several-files) | Reject a name declared in two files of one section, and a single-file section or extension key in two files |
| [K5.5](../../spec/contract.md#k5-contract-over-several-files) | A diagnostic about an element of a fragment names the fragment and the place in it |
| [K5.6](../../spec/contract.md#k5-contract-over-several-files) | The bundled form is valid against the contract schema, a fragment against `$defs/fragment` |

| Code | Meaning |
|---|---|
| `RIALTO-K001` | A contract or fragment is not valid YAML or JSON, or is not a mapping |
| `RIALTO-K002` | A contract, a fragment or `include` violates the JSON Schema |
| `RIALTO-K003` | A fragment whose `rialto` version differs from the root's |
| `RIALTO-K005` | A name declared twice, also across fragments |
| `RIALTO-K007` | An `include` path matches no file |
| `RIALTO-K008` | A fragment declares `info`, `sources` or `include` |
| `RIALTO-K009` | A single-file section or top-level extension key appears in two files |

All codes are in the [standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes).
