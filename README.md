# Rialto Specification

[![](https://img.shields.io/badge/Buijs-Software-blue)](https://buijs.dev/)

**A contract-driven architecture for generated applications.**

Specification 1.0.0, in development: built in slices, see [Status](#status).

## What Rialto is

Rialto is a contract-driven architecture for describing software declaratively across all architectural layers and generating its infrastructure, 
while generated code and handwritten business logic stay strictly separate.
Instead of replacing established standards, Rialto acts as the architectural backbone that connects them:
- **OpenAPI** for HTTP/REST contracts
- **AsyncAPI** for messaging and event streams
- **SQL** for persistence schemas

At its center is the **Rialto contract**: a single document that binds external contracts, domain models, mappings, storage definitions, and view models into one unified source of truth. 
Independent generators across languages (JVM, Dart, TypeScript, Go, etc.) read the same contract and produce code that agrees on identity, constraints, wire formats, and database mappings without drift.

It consists of:
- **the specification** (this repository): principles, terminology, the contract format, profiles for all architectural layers, and rules for generated code;
- **an open ecosystem of tooling and generators**: validation tools, parsers, CLI utilities, build plugins, and language-specific code generators (see [Tooling](docs/tooling.md)).

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

The full version of this contract, with its OpenAPI, AsyncAPI and SQL documents, is the
Shipment example, which follows in a later slice.

### What is possible with Rialto

- **Single architectural truth**: Model domain entities, relations, validation rules, REST routes, asynchronous events (AsyncAPI), object mappings, and database persistence in one cohesive contract.
- **Cross-language interoperability**: Independent generators in different languages (JVM, Dart, Go, Rust, TypeScript, etc.) produce components that communicate cleanly over the wire without sharing runtime library dependencies.
- **Strict seam architecture**: Generated adapters handle infrastructure concerns (routing, serialization, schema validation, persistence, transactions). Business logic lives behind explicit, protected seams that are never touched when regenerating contracts.
- **Early validation in CI/CD**: Contracts and external sources are validated together before any code is generated, catching breaking wire changes, schema conflicts, and undeclared capabilities early in the build pipeline.
- **Flexible authoring workflows**: Write contracts by hand in YAML/JSON, export them from existing annotated source code, or reference existing external specs.

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

Slice 0 brings the whole format, so a contract that uses any section is already valid or invalid against the
schema; what a section means, and the checks and test contracts of its profile, come with the slice of that profile.
The Shipment example grows with the slices.

## Reading order
1. [Overview](spec/overview.md): purpose, design rules, authoring, components, scope of version 1.
2. [Contract format](spec/contract.md) and its [JSON Schema](spec/contract-1.0.0.schema.json).
3. [Core](spec/core.md): terminology and the rules every generator follows.
4. Profiles, one per layer, in their slices.

Requirements use the keywords MUST, SHOULD, and MAY (BCP 14) and a stable identifier 
per document (C, K, A, D, E, L, R, M, P, Q, S, U, V). 
Each document ends with the rationale for its choices.

## Ecosystem and implementations

The Rialto specification is standalone, vendor-neutral, and not tied to any single repository or technology stack.
See [Tooling](docs/tooling.md) for the reference implementations and the [shared test contracts](examples/contracts/README.md)
for checking a tool against the specification.

See [CONTRIBUTING.md](CONTRIBUTING.md) for writing rules, [GOVERNANCE.md](GOVERNANCE.md) for how
decisions are made and the [changelog](CHANGELOG.md) for changes.

Licensed under the [Apache License 2.0](LICENSE).
