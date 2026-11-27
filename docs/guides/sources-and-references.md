# Sources and references

A contract builds on the documents a service already has: its OpenAPI document, its AsyncAPI document and its SQL
schema. This guide explains how a contract declares those documents under `sources`, how it points into them with
a `<source>#<location>` reference, and how an SQL source can be the migrations of a service. It is for contract
authors and for builders of Rialto tooling. It is informative: the rules are those of
[Sources and references](../../spec/contract.md#sources-and-references) and
[K1](../../spec/contract.md#k1-document), and this guide cites them rather than repeating them.

## Why

OpenAPI, AsyncAPI and SQL already describe the wire format, the event channels and the shape of the database, and
they have mature tooling. They stay the authoritative source for what they describe
([Sources of truth](../../spec/overview.md#sources-of-truth)). The contract does not copy them. It refers to their
elements and adds what they cannot express: how those elements correspond to each other and to the domain.

That gives three properties:

- **One place per fact.** A schema, a channel or a column is defined once, in the document that owns it. The
  contract only points at it.
- **Checked references.** Every reference must resolve to exactly one element (K1.2). A reference to a schema, table
  or column that does not exist fails validation with `RIALTO-S002`. A tool diagnoses contradictions between the
  sources instead of letting one redefine another ([C5.3](../../spec/core.md#c5-validation-configuration-and-diagnostics)).
- **No second schema.** An SQL source can point at the migrations of a service (K1.9). The schema the contract checks
  against is the one the migrations produce, not a hand-kept copy.

## How it works

```yaml
rialto: "1.0.0"
info: {name: shipment, version: 2.0.0}
sources:
  api: {kind: openapi, path: openapi.json, version: 2.0.0, status: current}
  db: {kind: sql, path: "db/migration/*.sql", dialect: postgresql}
types:
  Shipment: {kind: entity, identity: [id], properties: {id: {type: uuid}}}
mappings:
  - {source: api#/components/schemas/Shipment, target: Shipment, direction: toTarget}
storage:
  Shipment: {table: db#shipment, columns: {id: public_id}}
```

- **A source** has a short name under `sources`, such as `api` or `db`. The name starts with a lowercase letter and
  holds only letters and digits: `apiV2`, not `api-v2`.
- **`kind`** is `openapi`, `asyncapi` or `sql`.
- **`path`** is relative to the contract, or an `https` URL. A source at a URL is a remote source: it is pinned in the
  lock of the contract, as the guide [Remote sources and the lock](remote-sources.md) explains.
- **`version` and `status`** are required for an `openapi` or `asyncapi` source, and not allowed for an `sql`
  source. `status` is `current` or `deprecated`. A contract can list several versions of one API as separate sources.
- **`deprecated`, `sunset` and `successor`** belong to a source with `status: deprecated`. `deprecated` is then
  required. `successor` names another source of the contract.
- **`dialect`** is required for an `sql` source, and not allowed for the others.

A source entry that breaks these rules is `RIALTO-K002`: the JSON Schema checks them (K1.7).

### References

A reference has the form `<source>#<location>`. What the location is depends on the kind of the source:

| Kind | Location | Example |
|---|---|---|
| `openapi`, `asyncapi` | a JSON Pointer ([RFC 6901](https://www.rfc-editor.org/rfc/rfc6901)) into the document | `api#/components/schemas/Shipment` |
| `sql` | `table` or `table.column` | `db#shipment`, `db#shipment.version` |

A name without `#` refers to an element of the contract itself, such as a type, an operation or a view.

In `storage`, the `table` is a reference, such as `db#shipment`. A column under `columns` is a plain column name of
that table, such as `public_id`; it resolves as `db#shipment.public_id`.

### Migrations

An `sql` source is one SQL file, or the migrations of a service: a `path` with `*` or `**`, as in
[`include`](../../spec/contract.md#contract-over-several-files). `*` matches any characters within one segment of the
path, `**` any number of segments.

```sql
-- db/migration/V1__create_shipment.sql
CREATE TABLE shipment (public_id UUID PRIMARY KEY, status TEXT NOT NULL);
```

```sql
-- db/migration/V2__add_version.sql
ALTER TABLE shipment ADD COLUMN version BIGINT NOT NULL DEFAULT 0;
```

The schema is the result of applying the matched files in version order (K1.9). The version is the number after a
leading `V` up to `__`, compared part by part, so `V1.10__` comes after `V1.9__`. Files without a version come after
the versioned ones, in code point order of their path. After the two files above, `db#shipment.version` resolves.

## Scenarios

### Loading a source

| Situation | What the tool does | Diagnostic |
|---|---|---|
| The file exists and can be read | Reads it; references into it can resolve | — |
| The file does not exist | Rejects the source | `RIALTO-S001` |
| An OpenAPI or AsyncAPI file is not valid YAML or JSON, or not a mapping | Rejects the source | `RIALTO-S001` |
| A migrations path matches one or more files | Reads them in version order as one schema (K1.9) | — |
| A migrations path matches no file | Rejects the source (K1.9) | `RIALTO-S001` |
| The path is a URL | Reads the source as a [remote source](remote-sources.md) | `RIALTO-S003`, `RIALTO-S004`, `RIALTO-S005` |
| A source cannot be loaded | Reports it at the `path` of the source, and still runs the other checks | `RIALTO-S001` |

### Resolving a reference

| Situation | What the tool does | Diagnostic |
|---|---|---|
| `api#/components/schemas/Shipment` points at an element of the document | Resolves it | — |
| The JSON Pointer points at nothing | Rejects the reference | `RIALTO-S002` |
| `db#shipment` names a table of the schema | Resolves it | — |
| `db#shipment.version` names a table without that column, or a table the schema lacks | Rejects the reference | `RIALTO-S002` |
| The name before `#` is not under `sources` | Rejects the reference | `RIALTO-K004` |
| The source is declared but could not be loaded | Reports nothing more: the `RIALTO-S001` of the source is the finding | — |

## Edge cases

| Situation | What happens |
|---|---|
| A location in an OpenAPI or AsyncAPI source without a leading `/`, such as `api#components/schemas/Shipment` | It is no JSON Pointer, so it does not resolve: `RIALTO-S002`. |
| A key with `/` or `~` in it, such as the path `/shipments` | Escaped as in RFC 6901: `~1` for `/`, `~0` for `~`. `api#/paths/~1shipments/get` is the GET operation of `/shipments`. |
| An SQL reference in another case than the DDL, such as `db#SHIPMENT` for `CREATE TABLE shipment` | Resolves: table and column names are compared without regard to case. |
| A source that no reference uses | It is still loaded. A missing file is `RIALTO-S001` ([`invalid/missing-source.yaml`](../../examples/contracts/invalid/missing-source.yaml)). |
| `V1.10__` and `V1.9__` | Compared part by part as numbers: `V1.9__` first. |
| A timestamp as version, such as `V20261120120000__` | A number like any other; it comes after `V10__`. |
| Migrations in subdirectories, with `db/**/*.sql` | Ordered by version over all directories, not per directory. |
| A file without a version, such as `a_repeatable.sql` | After every versioned file, in code point order of the path. |
| `db/**` | Matches every file below `db`, also one that is not SQL. |
| A `successor` that is not a source of the contract | `RIALTO-K004`. |
| Two versions of one API | Two sources, each with its own name, `version` and `status`, such as `apiV1` and `apiV2`. |
| A contract over several files | Only the root declares `sources`; a fragment that does is `RIALTO-K008` (K5.2). A reference in a fragment resolves against the sources of the root, and a local `path` is relative to the root. See the guide [Contracts over several files](contracts-over-several-files.md). |

## Design decisions

From the [rationale](../../spec/contract.md#rationale) of the specification:

- **References to OpenAPI and SQL instead of copies.** Those standards stay authoritative for wire and storage and
  keep their tooling; the contract adds only correspondence and meaning.
- **Migrations as a source (K1.9).** A service's schema exists as its migrations; pointing at them avoids a second,
  hand-kept schema file that drifts.
- **Standard diagnostic codes (K1.10).** Shared test contracts and multi-language tooling only agree on why an
  invalid contract failed when they report the same code for the same violation: `RIALTO-S001` for a source that
  cannot be read, `RIALTO-S002` for a reference that does not resolve.

Following from the requirements:

- **Every reference resolves to exactly one element (K1.2).** A contract with a reference that lands nowhere is
  rejected, not generated from.

## Requirements

| Requirement | In short |
|---|---|
| [K1.2](../../spec/contract.md#k1-document) | Every reference resolves to exactly one element |
| [K1.7](../../spec/contract.md#k1-document) | The contract, its `sources` included, is valid against the JSON Schema |
| [K1.9](../../spec/contract.md#k1-document) | Read migrations in version order; reject a path that matches no file |
| [K1.10](../../spec/contract.md#k1-document) | Report violations with the standard diagnostic codes |
| [K4](../../spec/contract.md#k4-remote-sources) | Remote sources; see [Remote sources and the lock](remote-sources.md) |
| [K5.2](../../spec/contract.md#k5-contract-over-several-files) | A fragment declares no `sources` |

| Code | Meaning |
|---|---|
| `RIALTO-K002` | A source entry violates the JSON Schema, such as an `sql` source without `dialect` |
| `RIALTO-K004` | A reference names a source that is not declared, or a `successor` is not a source |
| `RIALTO-K008` | A fragment declares `sources` |
| `RIALTO-S001` | A source file cannot be read or parsed, or a migrations path matches no file |
| `RIALTO-S002` | A reference `<source>#<location>` does not resolve |

All codes are in the [standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes).
