# Rialto Specification

[![](https://img.shields.io/badge/Buijs-Software-blue)](https://buijs.dev/)

**A contract-driven architecture for generated applications.**

Specification 1.0.0, in development: it is built in slices, see [Status](#status).

## Contents

- [What Rialto is](#what-rialto-is)
- [Getting started](#getting-started)
- [Principles](#principles)
- [Status](#status)
- [Reading order](#reading-order)
- [Ecosystem and implementations](#ecosystem-and-implementations)

## What Rialto is

With Rialto you describe a service once, in a **Rialto contract**: its domain types, its operations, its events, how
it is stored and how it is shown. Generators read that contract and produce the infrastructure code. Your business
logic stays handwritten, and regenerating never touches it.

Rialto does not replace the standards you already use. It connects them:

- **OpenAPI** for HTTP and REST;
- **AsyncAPI** for messaging and event streams;
- **SQL** for the database schema.

The contract points into those documents instead of repeating them, and adds what they do not say: which domain type
an API schema is, which table holds it, which event it publishes. Generators in any language (JVM, Dart, TypeScript,
Go, …) read the same contract, so the code they produce agrees on identity, constraints, wire formats and columns.

Rialto consists of:

- **the specification** (this repository): the principles, the terms, the contract format, a profile per
  architectural layer and the rules for generated code;
- **an open ecosystem of tools and generators**: validators, command line tools, build plugins and code generators per
  language (see [Tooling](docs/tooling.md)).

### How Rialto connects contracts

```yaml
rialto: "1.0.0"
info: {name: shipment, version: 2.0.0}

# 1. Refer to the standard documents that stay authoritative
sources:
  api:    {kind: openapi, path: openapi.json, version: 2.0.0, status: current}
  events: {kind: asyncapi, path: asyncapi.json, version: 1.0.0, status: current}
  db:     {kind: sql, path: "db/migration/*.sql", dialect: postgresql}

# 2. Declare the domain: identity, presence and constraints
types:
  Shipment:
    kind: entity
    identity: [id]
    properties:
      id: {type: uuid}
      note: {type: string, nullable: true, maxLength: 280}
  ShipmentApproved:
    kind: value
    properties:
      shipmentId: {type: uuid}

# 3. Say which OpenAPI schema corresponds to which domain type
mappings:
  - {source: api#/components/schemas/Shipment, target: Shipment, direction: both}

# 4. Say which table and columns hold it
storage:
  Shipment:
    table: db#shipment
    columns: {id: public_id, note: delivery_note}

# 5. Publish a domain event and hand it to an authored handler
events:
  ShipmentApproved:
    type: com.example.shipment.approved.v1
    source: /shipments
    subject: shipmentId
    data: ShipmentApproved
    channel: events#/channels/shipmentEvents
    mode: structured
subscriptions:
  notifyWarehouse:
    event: ShipmentApproved
    handler: authored
    delivery: {attempts: 5, deadLetter: events#/channels/shipmentEventsDeadLetter}
```

The full version of this contract, with its OpenAPI, AsyncAPI and SQL documents, becomes the Shipment example in a
later slice.

### What Rialto gives you

- **One source of truth.** Entities, validation rules, REST routes, events, mappings and storage live in one contract.
- **Components that work together across languages.** Code from different generators talks over the wire without
  sharing a runtime library.
- **Generated code and your code stay apart.** Generated adapters handle routing, serialization, validation,
  persistence and transactions. Your business logic sits behind explicit seams that regeneration never touches.
- **Mistakes found before any code exists.** The contract and its sources are checked together, so a broken
  reference or an incompatible change fails the build, not production.
- **Write it the way you like.** By hand in YAML or JSON, exported from annotated source code, or a mix.

## Getting started

**Write a contract.** Start from the example above and point your editor at the
[JSON Schema](spec/contract-1.0.0.schema.json) for completion and checks while you type. The
[contract format](spec/contract.md) explains every section.

**Check it.** A validator such as [rialto-jvm](https://github.com/buijs-dev/rialto-jvm) checks the contract and every
reference into its sources:

```shell
rialto validate shipment.rialto.yaml
```

Every problem comes with a standard code, such as `RIALTO-K004` for an unknown type, and the file and line it is in.

**Build a tool.** Run it over the [shared test contracts](examples/contracts/README.md) to see whether it follows the
specification:

```shell
python3 tools/conformance.py -- my-tool validate {contract}
```

## Principles

1. **Entity-driven, contract-centered.** Applications are modeled as entities and operations. 
The contract is the one place every tool reads from and writes to, 
whether it is written by hand or exported from annotated code.
2. **Unambiguous.** Everything two generated components depend on to work together is 
explicit in the contract. Matching names never imply meaning.
3. **Open.** Where several good conventions exist, such as cursor or offset pagination, 
Rialto specifies each of them fully and the contract selects one. 
Frameworks may be opinionated; the specification is not.
4. **No silent information loss.** Absent, null and value stay distinct; 
no truncation, wrap-around or invented defaults.
5. **Fail early.** What can be checked during generation fails during generation; 
the rest fails visibly at runtime.
6. **Generated adapters, authored decisions.** Generated code handles technical concerns; 
business logic is handwritten and reached through explicit, replaceable seams. 
Regeneration never touches authored code.
7. **Build-time generation, no runtime lock-in.** Generated code needs no generator 
at runtime and only declared, minimal dependencies.

How a contract comes into being is free: written by hand, exported from annotated source code, or a mix.

## Status

The specification is built towards 1.0.0 in slices. Each slice is one vertical piece through the
specification, its test contracts and documentation, and the tooling and generators that implement it.

| Slice | Content | Status |
|---|---|---|
| 0 | Foundation: the whole contract format and its [JSON Schema](spec/contract-1.0.0.schema.json), [core](spec/core.md) (C1–C8), [contract](spec/contract.md) (K), the shared test contracts for the format, the tools | this repository |
| 1 | Domain and mapping profiles (D, M) | planned |
| 2 | REST and errors profiles (R, E) | planned |
| 3 | Persistence profile (P) | planned |
| 4 | Query profile (Q) | planned |
| 5 | Lifecycle profile (L) | planned |
| 6 | Auth profile (S) | planned |
| 7 | Events profile (A) | planned |
| 8 | Presentation profile (U) | planned |
| 9 | Versioning profile (V) and compatibility | planned |
| 10 | Ecosystem: generators, conformance levels and the generator protocol (C9) | planned |

Slice 0 brings the whole format, so every section of a contract can already be checked against the schema. What a
section means, with the checks and test contracts of its profile, comes with the slice of that profile. The Shipment
example grows with the slices.

## Reading order

1. [Overview](spec/overview.md): purpose, design rules, authoring, components, scope of version 1.
2. [Contract format](spec/contract.md) and its [JSON Schema](spec/contract-1.0.0.schema.json).
3. [Core](spec/core.md): terminology and the rules every generator follows.
4. Profiles, one per layer, in their slices.

Every requirement has a stable id, such as `K1.2`, with a letter per document (C, K, A, D, E, L, R, M, P, Q, S, U,
V), and uses the keywords MUST, SHOULD and MAY (BCP 14). Every document ends with the rationale for its choices.

## Ecosystem and implementations

The specification stands on its own: it is vendor-neutral and not tied to one repository or technology stack. Anyone
may build tools or generators for it. See [Tooling](docs/tooling.md) for the reference implementations, and the
[shared test contracts](examples/contracts/README.md) for checking a tool against the specification.

See [CONTRIBUTING.md](CONTRIBUTING.md) for writing rules, [GOVERNANCE.md](GOVERNANCE.md) for how
decisions are made and the [CHANGELOG.md](CHANGELOG.md) for changes.

Licensed under the [Apache License 2.0](LICENSE).
