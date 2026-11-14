# Contract format

Status: Contract format 1.0.0, part of the draft of Specification 1.0.0. The format is final when the specification reaches 1.0.0.

A Rialto contract is one document, in YAML or JSON, that describes an application for all profiles; it can be written as [several files](#contract-over-several-files). This document defines the envelope, the type system and references. Each profile defines its own section. The structure is formalized in the JSON Schema [contract-1.0.0.schema.json](contract-1.0.0.schema.json). Requirements use the prefix K.

## Example

Abridged from `shipment.rialto.yaml`, the Shipment example:

```yaml
rialto: "1.0.0"
info: {name: shipment, version: 2.0.0}
sources:
  api: {kind: openapi, path: openapi.json, version: 2.0.0, status: current}
  db: {kind: sql, path: schema.sql, dialect: postgresql}
types:
  ShipmentId: {kind: value, wraps: uuid}
  Shipment:
    kind: entity
    identity: [id]
    properties:
      id: {type: ShipmentId}
      note: {type: string, nullable: true, maxLength: 280}
mappings:
  - {source: api#/components/schemas/Shipment, target: Shipment, direction: both}
storage:
  Shipment: {table: db#shipment, columns: {id: public_id, note: delivery_note}}
```

## Document

YAML and JSON represent the same data model. A YAML contract uses only what JSON can express: string keys, no custom tags.

| Key | Required | Content | Defined in |
|---|---|---|---|
| `rialto` | yes | contract format version, a string such as `"1.0.0"` | this document |
| `info` | yes | `name` and `version` (SemVer) of this contract | this document, versioning |
| `sources` | no | external documents the contract refers to | this document |
| `include` | no | the fragments of a contract over several files | this document |
| `types` | no | entities, value objects, enums and projections | domain |
| `shapes` | no | derived input and output shapes | domain |
| `operations` | no | operations and their REST counterparts; list operations | REST, query |
| `errors` | no | error format, categories and application codes | errors |
| `events`, `subscriptions`, `streams` | no | domain events, their channels, consumers, and streams to browsers and apps | events |
| `auth` | no | providers, clients, claims and scopes | auth |
| `mappings` | no | correspondence between representations | mapping |
| `storage` | no | correspondence with tables and columns | persistence |
| `views` | no | screens, fields, actions and slots | presentation |
| `navigation` | no | the menu of the application | presentation |

Keys starting with `x-` are extensions. An extension for one generator is named after it, `x-<generator>-<name>`, such as `x-acme-csv`. Any other unknown key is an error (C5.8).

Where a profile offers several strategies for a concern, such as pagination, the contract selects one explicitly; there are no implicit defaults (see [design rules](overview.md#open-through-strategies), C8.3).

## Sources and references

`sources` maps a short name to an external document: `kind` (`openapi`, `asyncapi` or `sql`), `path` relative to the contract or an `https` URL, `version` and `status` for `openapi` and `asyncapi` sources, and `dialect` for `sql` sources. A contract can list several versions of an API (see versioning).

An SQL source can also be a service's migrations: its `path` then contains `*` or `**`, as in [`include`](#contract-over-several-files), such as `db/migration/*.sql`. The schema is the result of applying the matched files in version order: the version is the number after a leading `V` up to `__`, compared part by part (`V1.10__` after `V1.9__`); files without a version follow in code point order.

A reference has the form `<source>#<location>`:

| Kind | Location | Example |
|---|---|---|
| `openapi`, `asyncapi` | JSON Pointer ([RFC 6901](https://www.rfc-editor.org/rfc/rfc6901)) | `api#/components/schemas/Shipment` |
| `sql` | `table` or `table.column` | `db#shipment`, `db#shipment.version` |

Names without `#` refer to elements of the contract itself: a type, shape, operation or view name, or a property path such as `destination.street`.

**Remote sources.** A source at an `https` URL, such as the OpenAPI document another team publishes, is pinned in `rialto.lock` next to the contract: the SHA-256 of its content, in lowercase hexadecimal, per URL. The lock is committed with the contract, so every build reads the same document until it is updated on purpose.

```yaml
# rialto.lock
sources:
  "https://api.example.com/shipments/openapi.json": "3f2a…9c1e"
```

## Contract over several files

A contract can be written as a root and fragments. The root holds `rialto`, `info` and `sources`, and lists its fragments under `include`. A fragment holds `rialto` and any of the sections, never `info`, `sources` or `include`.

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

`include` lists paths relative to the root. In a path, `*` matches any characters within one segment and `**` any number of segments. The matched files are read in code point order of their path; a file matched twice is read once. The sections merge as follows:

| Section | Merge |
|---|---|
| `types`, `shapes`, `operations`, `events`, `subscriptions`, `streams`, `storage`, `views` | per name; a name is declared in one file only |
| `mappings` | concatenated: the root first, then the fragments in reading order |
| `errors`, `auth`, `navigation`, extension keys at the top level | in one file only |

Names and references work across files: a fragment may refer to a type of another fragment, and every `source#location` resolves against the `sources` of the root.

The merged contract, without `include`, is the **bundled form**. It is the exchange format: what is published, compared between versions and read by generators of other languages. It is valid against the contract schema; a fragment is valid against its `$defs/fragment`.

## Types

Every type has one JSON representation, used wherever a value crosses a process boundary (HTTP bodies, query values, cursors in readable form). An OpenAPI document may only narrow it, for example by sending an `int64` as a string.

**Scalars**

| Type | Values | JSON representation |
|---|---|---|
| `boolean` | true, false | `true`, `false` |
| `int32`, `int64` | signed integers of that width | number; an `int64` may be a string where OpenAPI says so |
| `decimal`, `decimal(p,s)` | exact decimal number, optionally with at most `p` digits of which `s` after the point | number or string, as OpenAPI says |
| `float64` | IEEE 754 binary64, without NaN and infinities | number |
| `string` | Unicode text | string |
| `uuid` | UUID ([RFC 9562](https://www.rfc-editor.org/rfc/rfc9562)) | string, lowercase on output |
| `date` | calendar date | `full-date` ([RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)): `2026-10-31` |
| `time` | local time of day | `partial-time` (RFC 3339): `09:30:00` |
| `localDateTime` | date and time without offset or zone | `full-date "T" partial-time` (ISO 8601): `2026-10-31T09:30:00` |
| `instant` | point in time | `date-time` (RFC 3339); output in UTC with `Z` |
| `offsetDateTime` | point in time with its UTC offset | `date-time` (RFC 3339), offset kept: `2026-10-31T09:30:00+01:00` |
| `zonedDateTime` | point in time in a named time zone | RFC 3339 with time zone suffix ([RFC 9557](https://www.rfc-editor.org/rfc/rfc9557)): `2026-10-31T09:30:00+01:00[Europe/Amsterdam]` |
| `duration` | exact amount of time | ISO 8601 duration with days, hours, minutes and seconds only, a day being 86 400 s: `P1DT2H30M` |
| `period` | calendar amount | ISO 8601 duration with years, months and days only: `P1Y2M10D` |
| `bytes` | binary data | base64 ([RFC 4648](https://www.rfc-editor.org/rfc/rfc4648) §4) |
| `json` | any JSON value, not interpreted | the value itself ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)) |
| `binary` | a stream of bytes with a media type, such as a photo or a PDF | none: a whole request or response body, or a part of `multipart/form-data` (REST, R7) |

**Collections:** `list<T>` (ordered; in storage, by a declared order, P4.13), `set<T>` (unique) and `map<K, V>`, where `K` is `string`, `uuid`, `int32`, `int64`, `date` or an enum, written as its JSON string form when used as an object key. A `?` after a type argument allows null elements: `list<string?>`. Collections of collections are not supported in this version.

**Named types** are declared under `types` with a `kind`: `entity`, `value`, `enum`, `union` or `projection` (see domain). An enum with `extensible: true` accepts members that were added later; a union is one of several declared variants:

```yaml
types:
  PaymentMethod: {kind: enum, members: [card, invoice], extensible: true}
  Payment:
    kind: union
    discriminator: method
    variants: {card: CardPayment, invoice: InvoicePayment}
```

**Properties** are declared per type:

| Key | Meaning |
|---|---|
| `type` | scalar, collection or named type |
| `nullable` | null is an allowed value (default false) |
| `minLength`, `maxLength`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`, `minItems`, `maxItems`, `uniqueItems`, `pattern`, `format` | constraints, with the semantics of JSON Schema validation ([2020-12](https://json-schema.org/draft/2020-12/json-schema-validation)); `pattern` uses ECMA-262 regular expressions and `format` the formats defined there, such as `email` and `uri` |
| `maxSize`, `mediaTypes` | for a `binary`: the largest size in bytes (required), and the media types it may have, such as `application/pdf` or `image/*` (default any) |
| `relation` | for a property of entity type: `owned` or `reference` |
| `requiredWhen`, `absentWhen`, `minimumOf`, `maximumOf` | rules on another property of the same type (domain, D3.6, D3.7) |
| `immutable` | true when the value is set at creation and never changes afterwards (L1.6) |
| `description` | what the property means, in CommonMark |

Nullability is a property of the type; presence (absent or supplied) is a property of a shape or operation. They are declared separately (C3.1).

**Descriptions.** Types, properties, shapes, operations, events and error codes can carry a `description` in CommonMark, as in OpenAPI and AsyncAPI. A description documents; it never changes generated behavior.

```yaml
Shipment:
  kind: entity
  description: A shipment from a warehouse to a destination.
  properties:
    note: {type: string, nullable: true, description: Free note for the driver.}
```

## Standard diagnostic codes

Every contract validator and generator reports contract validation errors with these diagnostic identifiers (C5.11, K1.10). The letter after `RIALTO-` is the area of the check, not a requirement prefix: `K` the contract itself, `S` its sources, `P` the rules of a profile (the last column names the requirement). A tool may define further codes for its own checks, such as generation or export, with other letters and documents them (C5.11).

| Code | Meaning | Requirements |
|---|---|---|
| `RIALTO-K001` | Document is not valid YAML or JSON, or is not a mapping | K1.7 |
| `RIALTO-K002` | Contract or fragment violates the JSON Schema (such as an unknown key or wrong value type) | C5.8, K1.7, K5.6 |
| `RIALTO-K003` | Unsupported `rialto` version, or a fragment whose `rialto` version differs from the root's | C5.7, K1.1, K5.3 |
| `RIALTO-K004` | Unresolved reference to a contract element (type, shape, operation, event or view) | K1.2 |
| `RIALTO-K005` | Duplicate name within `types` and `shapes`, within a section, or across fragments | K1.3, K5.4 |
| `RIALTO-K006` | Invalid type expression, such as a map key that is not an allowed scalar or enum | K2.1 |
| `RIALTO-K007` | An `include` path matches no file | K5.2 |
| `RIALTO-K008` | A fragment declares `info`, `sources` or `include` | K5.2 |
| `RIALTO-K009` | A single-file section (`errors`, `auth`, `navigation`) or top-level extension key appears in two files | K5.4 |
| `RIALTO-S001` | A declared source file cannot be read or parsed, or an SQL migration path matches no file | K1.2, K1.9, K4.3 |
| `RIALTO-S002` | An external reference (`<source>#<location>`) does not resolve | K1.2 |
| `RIALTO-S003` | A remote source can neither be fetched nor found in the cache | K4.3 |
| `RIALTO-S004` | A remote source differs from its hash in `rialto.lock` | K4.2 |
| `RIALTO-S005` | A remote source does not use `https` | K4.4 |
| `RIALTO-P001` | An entity identity property does not exist on the entity | D2.2 |
| `RIALTO-P002` | Union variants mix entities and value objects, a variant is a union, or entity variants do not share one identity type | D2.6 |
| `RIALTO-P003` | Query field is not a supported scalar, enum or wrapper (or is `json`), or operator does not apply to the field's type | K2.10, Q1.1, Q1.2 |
| `RIALTO-P004` | List `tiebreaker` is not a sortable, unique, non-nullable query field | Q1.3 |
| `RIALTO-P005` | Operation lists an undeclared error code (an application code that reuses a standard code name violates the JSON Schema, `RIALTO-K002`) | E1.1 |
| `RIALTO-P006` | Invalid property representation in a command shape (`as: identity`, `as: command` or `as: value`), or a read-only to-many reference in a command | L1.2, P4.12 |
| `RIALTO-P007` | The `version` of an OpenAPI or AsyncAPI source does not equal `info.version` of the document | V1.4 |
| `RIALTO-P008` | A scope used in an OpenAPI security requirement of a referenced operation is not declared under `auth.scopes` | S1.1 |
| `RIALTO-P009` | A `list.wire` parameter or response pointer does not resolve in the OpenAPI operation, or has an incompatible type | Q1.4 |
| `RIALTO-P010` | An `errors.wire` pointer does not resolve in the operation's error response schema, or a declared status is missing | E1.2, E1.3 |
| `RIALTO-P011` | An event `subject` does not resolve in its `data` type, an event `type` is not unique, or `channel` or `deadLetter` does not resolve in the AsyncAPI source | A1.1, A1.2 |
| `RIALTO-P012` | A union variant declares the discriminator property with a type other than `string`, or variants share a discriminator value | K2.8 |
| `RIALTO-P013` | A REST list operation omits `wire` or filter and sort encodings, a local list operation declares `wire`, or a `fixed` sort declares a sort parameter or encoding | Q1.6, Q3.1 |
| `RIALTO-P014` | A shape property constraint weakens the source property's constraint or does not apply to the property's type (`uniqueItems` applies to `list<T>` only) | C5.4, D3.5, D3.8 |
| `RIALTO-P015` | A REST operation parameter is not mapped in `parameters`, or a mapped parameter or property path does not resolve | R1.5 |
| `RIALTO-P016` | With `identify: type`, `codeTypes` does not contain exactly one `{code}`, or two codes, or a code and a category, have the same `type` URI | E2.2 |
| `RIALTO-P017` | A deprecated operation is not marked `deprecated: true` in its OpenAPI operation | V2.2 |
| `RIALTO-P018` | With `locationFormat: path`, a top-level property of a request body has the name of a parameter or header of the same operation | E1.5 |
| `RIALTO-P019` | A count operation does not declare the filter parameter of the list it counts, or requires a parameter the list operation does not have | Q5.2 |
| `RIALTO-P020` | A `conditional` operation is not a GET or HEAD, or its OpenAPI operation lacks the `If-None-Match` header, an `ETag` on its success response or a 304 response | R6.1 |
| `RIALTO-P021` | A `binary` property has no `maxSize`, is an element of a collection or a map value, is a query field, or is in a type or shape an operation carries as JSON | K2.11, R7.1 |
| `RIALTO-P022` | An OpenAPI `apiKey` scheme in the security of a referenced operation is not declared under `auth.apiKeys`, or is not sent in a header | S6.1 |
| `RIALTO-P023` | A transition's state property is not a closed enum whose default is a member, a `from` (of a rule or a delete) or `to` is not a member, `transition` (or a rule of its `select`) names an unknown rule, or a command shape contains the state property | L5.1, L5.9 |
| `RIALTO-P024` | `idempotency` is declared on an operation with a safe method (GET, HEAD, OPTIONS), or its header is not a header parameter of the referenced OpenAPI operation | L3.2 |
| `RIALTO-P025` | A mapping entry names a property that neither side has, or leaves a required property of the side it produces without coverage, or uses `version: stored` without a stored version, or a path key does not name a property of a to-one owned child or value object | M1.2, M2.8, M2.9, M2.10 |
| `RIALTO-P026` | A property of a stored entity or projection has no column, child, link, blob or computed value, or more than one, two properties share a column, a storage key names no property, or a column's type or nullability, or the type of a join's `key` column, does not fit its property; or the `order` column of a list is not a `NOT NULL` integer column | P1.5, P1.6, P4.13 |
| `RIALTO-P027` | A batch `wire` pointer does not resolve in the OpenAPI operation, does not point to an array where one is required, or `index` or `status` does not point to an integer | L4.5 |
| `RIALTO-P028` | An update command shape has an `immutable` property | L1.6 |
| `RIALTO-P029` | A `link` operation does not name a to-many reference with a link table, its parameters do not address the owner and the target by identity, or it also declares `lifecycle`, `input` or `transition` | L6.1 |
| `RIALTO-P030` | A `unique` key names a property that is not stored in a column of the entity's table, or the path parameters of an operation address an entity by properties that are neither its identity nor a declared unique key | P3.6, R1.6 |
| `RIALTO-P031` | `deleted` is declared on an operation that does not read, or on an entity without soft deletion; a command carries a property on the marker or `by` column; a delete or restore names no entity, or a restore's storage lacks `restore: true`; a restore declares an `input`; `by` is the marker column, or `by` or `restore` is declared without `soft`; or `subject` is not an entity | P6.3, P6.10, L3.7, R1.7 |
| `RIALTO-P032` | `as: [identity, command]` is used outside a create command, on a property that is not a reference, without the create command shape of its type, or its mapping lacks a `from` per form | L1.7 |
| `RIALTO-P033` | An `output: list<T>` lacks `maxItems`, its success response is not an array, or it is also a `list` operation; or `maxItems` is declared without `output: list<T>` | R2.7 |
| `RIALTO-P034` | A `subject` with `by: actor` names no entity, maps a parameter to its identity, has an input that carries that identity, or belongs to an operation that needs no signed-in caller; or an operation that needs no signed-in caller has an input with a property with role `actor` | R1.8, S4.1 |
| `RIALTO-P035` | A `scope` names a column twice or a column the table lacks, storage entries on one table declare different scopes, a type references a type whose scope has a source it does not declare, a command carries a property on a scope column, or a type with an `actor` entry is reached by an operation that needs no signed-in caller | P6.11 |
| `RIALTO-P036` | A `select` names rules of several entities, its operation references no OpenAPI operation, or it does not resolve in a referenced request body to a string schema whose `enum` contains its keys; a `sets` key is not a property of the entity, or is its identity or state property, `now` names a property that is not an `instant`, `offsetDateTime` or `zonedDateTime` or a value type wrapping one, `null` one that is not nullable, the input of an operation that performs the rule contains the property, or the rule sets `actor` and an operation that needs no signed-in caller performs it; an operation lists an event in `emits` that a rule it performs emits as well; a create performs a rule whose `from` lacks the initial state; or `from` is declared on an operation that is not a delete, or for an entity without `transitions` | L5.6, L5.7, L5.8, L5.9, L5.10 |
| `RIALTO-P037` | An action's `values` pointer does not resolve in the request body of an OpenAPI operation of its operation, its value does not fit the schema there, or its value at the `select` of the operation's transition is not a key of its `rules` | U3.9 |
| `RIALTO-P038` | A `requiredWhen` or `absentWhen` names a property that is not another enum property of the type, a member it does not have, is declared on a non-nullable property, or both name one member; a `minimumOf` or `maximumOf` names a property that is not another property of the type with the same ordered scalar; or `uniqueItems` is declared on a property that is not a `list<T>` | D3.6, D3.7, D3.8 |
| `RIALTO-P039` | A `presence` entry is in a `toSource` mapping, its key is not a non-nullable boolean property of the target, its property is not a property of the source, or the source does not keep presence | M3.11 |
| `RIALTO-P040` | A join of two steps is on a collection, in a command or under `generated`; a join on a property without `relation` has a type that is not a scalar or a wrapper of one; a `computed` property is not a non-nullable `int32` or `int64`, is in a command or under `generated`, or counts a property that is not a to-many child or link of the entity | P2.11, P2.12, P2.13 |
| `RIALTO-P041` | A route has a parameter twice, or a route parameter fills properties of different scalars; a `navigation` entry or `home` names a view whose route has parameters, or a view twice, or its `badge` is not the count operation of the entry's list or requires a parameter; a view with tabs has no route, or a tab has no route, a route parameter its view lacks or fills with another scalar, or tabs of its own; a `link` or `open` names a view without a route, a link is on a view without data, or a route parameter the data cannot fill with a scalar of the same type | U5.3, U5.9, U5.10, U5.11 |
| `RIALTO-P042` | A row action's parameter has no source or more than one, or a named or found source is not one value of its scalar; `parameters` on an action that is not a row action, or a list view's own action whose parameter the route does not fill; a `where` names a field or operator the list operation does not declare, or a field that is not a `string` or `uuid`; a column does not resolve, crosses two collections or a map, or does not end at a scalar, enum or wrapper; `list.operation` is neither a list operation nor an `output: list<T>`, or is one and the view declares `filters`, `where` or `pageSize` | U3.10, U6.5, U6.6, U6.7 |
| `RIALTO-P043` | A `visibleWhen` or `enabledWhen` path does not resolve, crosses a collection, is not an enum property with the listed members, or for `actor` not a `string` or `uuid`; or the view has no data for it | U3.11 |
| `RIALTO-P044` | An `options` field does not edit a to-one reference of its operation's input, its operation does not return the referenced entity or a projection with its identity, has an `input`, or has a parameter that neither maps to `label` nor is filled from one route parameter, or `label` does not resolve to a scalar, enum or wrapper | U2.11 |
| `RIALTO-P045` | A `list<T>` under `children` or `links` declares neither `order` nor `orderBy`, or both; `order` or `orderBy` is declared on a `set<T>` or another type that is not a `list<T>`, or `order` on a link without a link table; the `order` column also holds a property, a key, the `version` or a column of a blob, a scope or a to-one child; or an `orderBy` entry names a property twice, or a property that the element type lacks or that is not a `string` or an ordered scalar | P4.13 |

**Machine-readable output (informative).** For editors and CI annotations, a validator can offer its findings as one JSON document, as the reference tooling does with `rialto validate --format json`. The form below is a recommendation, not a requirement; `file` is the file of the finding, which for a contract over several files is a fragment (K5.5), and `line`, `column`, `requirement` and `hint` are null when unknown.

```json
{
  "valid": false,
  "contracts": [{
    "file": "shipment.rialto.yaml",
    "valid": false,
    "diagnostics": [{
      "severity": "error", "code": "RIALTO-K004", "requirement": "K1.2",
      "file": "contract/shipment/operations.rialto.yaml", "line": 42, "column": 15,
      "pointer": "/operations/getShipment/output",
      "message": "Unknown type 'Shipmnt'", "hint": null
    }]
  }]
}
```

## Requirements

- **K1.1** A generator MUST reject a contract whose `rialto` version it does not support (C5.7).
- **K1.2** Every reference MUST resolve to exactly one element. A generator MUST reject a contract with an unresolved or ambiguous reference.
- **K1.3** Names MUST be unique within `types` and `shapes` together, and within `operations` and `views` each.
- **K1.4** A generator MUST ignore sections of profiles it does not implement, and MUST reject a request to generate from a section it does not support.
- **K1.5** Two generators that implement the same profile MUST give a contract the same meaning for everything this specification defines, whatever their language.
- **K1.6** Generator configuration, such as package names, output paths and code style, MUST NOT be part of the contract, except under `x-` keys.
- **K1.7** A generator MUST reject a contract that is not valid against the JSON Schema of its `rialto` version. The schema checks structure only; K1.2 and K1.3 are checked by the generator.
- **K1.8** A generator MUST ignore the extension keys of other generators. An extension MUST NOT change the meaning of anything this specification defines (K1.5).
- **K1.9** A tool MUST read the migrations of an SQL source in version order and resolve references against the resulting schema. It MUST reject a path that matches no file.
- **K1.10** A tool that validates a contract MUST report violations of the rules in the [standard diagnostic codes](#standard-diagnostic-codes) table with the identifier listed there (C5.11).

### K2. Types

Examples: test contracts [`invalid/map-key.yaml`](../examples/contracts/invalid/map-key.yaml).

- **K2.1** Generated code MUST represent every value of a scalar type exactly. `int64` and `decimal` values MUST NOT pass through binary floating point, also not when they are JSON numbers.
- **K2.2** A `decimal(p,s)` value with more than `p` digits or more than `s` fraction digits MUST be rejected with code `precision`; it MUST NOT be rounded.
- **K2.3** An `instant` MUST be written in UTC with `Z`; an `offsetDateTime` MUST keep its offset; a `zonedDateTime` MUST keep its zone name. A value of one of these types MUST NOT be converted into another except through a declared conversion (M3.1).
- **K2.4** `date`, `time` and `localDateTime` MUST NOT be converted from or into a point in time without a declared time zone.
- **K2.5** A `duration` with year or month components, and a `period` with time components, MUST be rejected.
- **K2.6** A generator whose regular expression engine differs from ECMA-262 MUST translate `pattern` faithfully, or reject a pattern it cannot translate.
- **K2.7** A value of a closed enum that is not a member MUST be rejected. A value of an extensible enum that is not a member MUST be preserved through decoding and encoding, and generated code MUST distinguish it from the declared members.
- **K2.8** Each variant of a union MUST have a distinct discriminator value. Encoding MUST write the variant's value in the discriminator property; decoding MUST select the variant by it, and MUST reject an unknown value. A variant need not declare the discriminator as a property; when it does, its type MUST be `string`.
- **K2.9** NaN and infinite `float64` values MUST NOT be produced; encoding one MUST fail.
- **K2.10** A `json` value MUST pass through as the same JSON value: numbers keep their exact value (K2.1) and no member is added or dropped. It has no constraints, and it MUST NOT be a query field.
- **K2.11** A `binary` property MUST declare `maxSize` and MUST NOT be an element of a collection, a map value or a query field. It has no JSON representation: a type or shape that an operation carries as JSON MUST NOT contain one (`RIALTO-P021`).

### K3. Descriptions

Examples: none yet: the scenarios of the Shipment example follow in a later slice.

- **K3.1** A `description` MUST NOT change the behavior of generated code. Two contracts that differ only in descriptions MUST produce code that behaves the same.
- **K3.2** A generator SHOULD emit descriptions as documentation comments in the generated code, so that code-first export reproduces them (C8.2).

### K4. Remote sources

Examples: test contracts [`invalid/missing-source.yaml`](../examples/contracts/invalid/missing-source.yaml).

- **K4.1** A tool MUST read a remote source only when the SHA-256 of its content equals the hash in `rialto.lock`. A remote source not in the lock yet MUST be fetched and added to it.
- **K4.2** A tool MUST reject a remote source whose content differs from its locked hash, and MUST NOT change a locked hash except by an explicit update command.
- **K4.3** A tool MUST be able to work offline from a cached copy that matches the lock, and MUST reject a remote source it can neither fetch nor find in its cache. It MUST NOT fall back to another version.
- **K4.4** A remote source MUST use `https`.

### K5. Contract over several files

Examples: test contracts [`invalid/duplicate-name.yaml`](../examples/contracts/invalid/duplicate-name.yaml), [`invalid/fragment-duplicate/`](../examples/contracts/invalid/fragment-duplicate/), [`invalid/fragment-include-missing/`](../examples/contracts/invalid/fragment-include-missing/), [`invalid/fragment-root-key/`](../examples/contracts/invalid/fragment-root-key/), [`invalid/fragment-single-section/`](../examples/contracts/invalid/fragment-single-section/), [`invalid/fragment-version/`](../examples/contracts/invalid/fragment-version/), [`invalid/unknown-key.yaml`](../examples/contracts/invalid/unknown-key.yaml), [`invalid/unsupported-version.yaml`](../examples/contracts/invalid/unsupported-version.yaml), [`valid/fragments/`](../examples/contracts/valid/fragments/).

- **K5.1** A tool MUST give a contract and its bundled form the same meaning. Bundling MUST NOT drop, change or reorder elements within a section.
- **K5.2** A tool MUST reject an `include` path that matches no file, and a fragment that declares `info`, `sources` or `include`.
- **K5.3** A tool MUST reject a fragment whose `rialto` version differs from the root's (K1.1).
- **K5.4** A tool MUST reject a name declared in two files of the same section (K1.3), and a section or top-level extension key that belongs in one file and appears in two.
- **K5.5** A diagnostic about an element of a fragment MUST name that fragment and the location in it (C5.1).
- **K5.6** The bundled form and every fragment MUST each be valid against the JSON Schema (K1.7): the bundled form against the contract, a fragment against `$defs/fragment`.

## Rationale

- **One document for all layers.** Cross-language generation needs one shared input; separate files per layer would need their own correspondence rules again.
- **References to OpenAPI and SQL instead of copies.** Those standards stay authoritative for wire and storage and keep their tooling; the contract adds only correspondence and meaning.
- **YAML and JSON.** YAML is pleasant to write, JSON easy to generate and validate; restricting YAML to the JSON data model keeps them equivalent.
- **No generator configuration in the contract.** The contract is shared between languages; package names and code style are not.
- **A JSON Schema, not prose only (K1.7).** Every language has a JSON Schema validator, so generators reject malformed contracts identically.
- **One JSON form per type (K2).** A backend and a frontend only agree on a value if they agree on its text. RFC 3339, RFC 9557, ISO 8601 and RFC 4648 already define these forms.
- **An uninterpreted `json` type (K2.10).** Some data, such as the raw response of another system kept for later processing, has no schema of its own; a typed contract can only carry it as opaque JSON, and saying so is better than a string with JSON inside.
- **Exact numbers (K2.1, K2.2).** Amounts of money and identifiers break silently when a JSON parser turns them into doubles; rounding hides the error instead of reporting it.
- **Instant, offset, zone and local time are different types (K2.3, K2.4).** "09:00 in Amsterdam", "09:00+01:00" and "08:00Z" are different facts once daylight saving time or a meeting place changes; converting implicitly loses the difference.
- **Extensible enums (K2.7).** A client released before a new member was added must keep working; preserving the unknown value is what makes adding members a compatible change.
- **Unions with a discriminator (K2.8).** It is how OpenAPI (`oneOf` with `discriminator`) and most languages (sealed types) express alternatives; decoding by trial is ambiguous. The discriminator belongs to the union and the wire, not to the variants: in Kotlin and Dart the variant's class already is the distinction.
- **Descriptions are documentation only (K3).** Behavior must follow from declarations a generator can check; prose cannot be checked. Copy shown to end users stays in message keys (U1.5), so it can be translated.
- **Standard diagnostic codes (K1.10).** Shared test contracts and multi-language tooling only agree on why an invalid contract failed when they report the same code for the same violation.
- **Pinned remote sources (K4).** A contract that refers to an API another team publishes must build the same way tomorrow; a hash makes an upstream change visible as a deliberate update with a diff, not a surprise in a later build.
- **Fragments merged by name, not by `$ref` (K5).** Elements of a contract already refer to each other by name, so files merge without an index of pointers, and a duplicate is the same error as in one file. JSON `$ref` would need such an index, and the bundlers built for OpenAPI do not read other kinds of documents.
- **One bundled form (K5.1).** How a team splits its files is its own choice; generators in other languages, compatibility checks and published contracts keep one document as input.
- **Migrations as a source (K1.9).** A service's schema exists as its migrations; pointing at them avoids a second, hand-kept schema file that drifts.
- **Extensions named after their generator (K1.8).** Two generators can then extend the same element without a clash, and a reader knows which generator gives a key meaning.
