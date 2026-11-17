# Core
Status: Specification 1.0.0-rc.1.

The rules every generator follows, whatever profile or platform. 
The keywords MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be 
interpreted as described in BCP 14 ([RFC 2119](https://www.rfc-editor.org/rfc/rfc2119), [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)) when, 
and only when, they appear in all capitals. Only numbered requirements are normative. 
Identifiers are stable; removed identifiers are not reused.

Requirements apply to a **generator**: the tool for one stack and the code it generates. 
A requirement of the form "A generator MUST document …" applies to its published documentation.

## Example

One generation run for the Shipment example, by a fictional Kotlin generator. The file names are its choice; what is generated and what is authored is not:

```text
build/generated/rialto/               generated output (C1.1)
  ShipmentMapper.kt
  ShipmentResource.kt
  manifest.json                       inputs, configuration and owned output set (C1.4)
src/main/kotlin/
  ApproveShipmentHandler.kt           authored: the seam approveShipment calls (C4.3, C6.6)
  Address.kt                          authored: the invariant of Address (D4.3)
```

Regeneration rewrites only the files in the manifest. It never touches `ApproveShipmentHandler.kt` (C1.2), and it does not delete a file under `build/generated/rialto/` that the manifest does not list (C1.5, C1.7).

Presence is kept apart from nullability where the contract declares a partial input (C3.1):

```text
PATCH /shipments/f79a…  {}                → note unchanged   absent
PATCH /shipments/f79a…  {"note": null}    → note cleared     present-null
PATCH /shipments/f79a…  {"note": "Gate"}  → note set         present-value
```

A generated type that turns the first two into the same `note = null` violates C3.1. When a contract cannot be generated, the diagnostic is actionable (C5.1, C5.11, C5.12):

```text
error RIALTO-P004 shipment.rialto.yaml:612:9 operations.listShipments.list.sort.tiebreaker
  'note' is not a unique, non-nullable query field (Q1.3); generation failed
```

## Terminology
**Absent, present-null, present-value**, the three presence states of an input property:
not supplied, supplied as null, supplied with a value.
Presence is independent of nullability, which says whether null is an allowed value.

**Authored code** is everything (code or otherwise) written by people: 
business logic, custom adapters and converters, custom UI components, the contract itself. 
A generator never owns authored code.

**Authoritative source** is the input that defines the truth for one concern, 
such as an OpenAPI document for the wire format (see [Sources of truth](overview.md#sources-of-truth)).

**Authoring mode** is how a contract comes into being: 
written by hand (contract-first), exported from annotated source code (code-first), or both (mixed).

**Capability** is an optional part of a profile, identified as `<profile>.<name>`, 
such as `persistence.optimistic-concurrency`. A profile lists which requirements apply 
only when a generator supports the capability; all other requirements apply to every generator of that profile.

**Contract** is the Rialto document describing an application ([contract format](contract.md)).

**Correlation** is a declared statement that elements of two representations
stand for the same concept or property.

**Declared** means stated explicitly in the contract, or, where a requirement says so,
in the generator's documentation or the generator configuration.

**Default** is a value used when a property is absent.
Its *phase* says where it is applied: when decoding a transport representation,
in business logic, or in the database.

**Diagnostic** is a message from a generator reporting an error or warning.
It is *actionable* when it names the input location, the rule involved, and whether the run failed.

**Entity, value object, projection**, three kinds of concept:
an *entity* has an identity that persists while its state changes,
a *value object* is defined entirely by its values,
and a *projection* is a selected read-only shape of one or more concepts.

**Exporter** is a tool that reads source code or other inputs and produces a contract.

**Field binding** is the association between a UI element and a property path.
"Binding" alone is used only for field and operation bindings,
and for protocol bindings as CloudEvents defines them.

**Generated output** is the set of files a generation run produces
and may overwrite or remove on the next run.

**Generation rejection, execution failure**, the two ways generation or generated code fails:
a generation rejection stops a component from being generated or compiled,
an execution failure happens when generated code meets a value it cannot process.
Successful generation does not mean every runtime value is valid.

**Generator** is a tool that produces code from a contract for one stack
(language, frameworks, runtime libraries) and realizes one or more profiles,
together with its generator configuration and documentation.

**Generator configuration** is the set of stack-specific settings for one generator,
such as package names, output paths, and code style.
It is defined by the generator and never part of the contract.

**Identity** is the set of properties that distinguish one instance of an entity from another,
independent of names in any representation.

**Input source** is where generated code gets a value that is not in the request,
such as the tenant from the security context.

**Normalization policy** is a declared rule defined by a profile that turns a supplied value into a different one,
such as `nullAs: empty` turning null into an empty collection.
The contract selects a policy per property; the generator lists which policies it supports.

**Operation binding** is the association between a generated load, submit or action and a declared operation,
including its input, output, failure and concurrency behavior.

**Owned output set** is the exact set of files a generation run declares as its output (C1.4).

**Ownership transition** is an explicit step by which a generated file,
such as a scaffold, becomes authored code (C1.3).

**Profile** is the part of the specification for one concern:
domain, REST, mapping, persistence, query, errors, lifecycle, versioning, events, auth, or presentation.

**Provenance** is where a piece of metadata came from:
file, location, and, for layered configuration, the layer.

**Query parameter** is a value passed to a storage query separately from the query text,
so it is never parsed as query syntax.

**Representation** is a concrete shape of a concept:
a domain type, transport DTO, table row, or view model.

**Runtime dependency** is a library that generated code needs at runtime.

**Seam** is a documented point where application code customizes or replaces a generated component:
an interface, callback, registration, slot, or override.

**Strategy** is one of a closed set of fully specified conventions for a concern,
such as `cursor` or `offset` pagination.
A profile defines the set; the contract selects one.

## C1. Generated and authored code

Examples: none yet: the scenarios of the Shipment example follow in a later slice.

- **C1.1** A generator MUST distinguish generated output from authored code.
- **C1.2** Regeneration MUST NOT overwrite authored code.
- **C1.3** A generated scaffold that becomes authored code MUST have an explicit ownership transition and MUST NOT later be treated as generated output.
- **C1.4** Each generation run MUST declare its inputs, configuration, and owned output set.
- **C1.5** Cleanup MUST remove only owned output.
- **C1.6** Conflicting output ownership MUST be diagnosed.
- **C1.7** Before writing or cleaning, a generator MUST reject an output location that resolves outside its output roots, including through symbolic links. It MUST NOT delete an authored file because it is located under an output root.

## C2. Concepts and representations

Examples: none yet: the scenarios of the Shipment example follow in a later slice.

- **C2.1** A generator MUST preserve declared correlation. Equal names MUST NOT be taken to mean equal meaning where correlation is ambiguous.
- **C2.2** Identity MUST remain independent of transport field names and column names.
- **C2.3** A generator MUST report an unsupported type or relationship instead of substituting a lossy one.

## C3. Presence, nullability, and defaults

Examples: none yet: the scenarios of the Shipment example follow in a later slice.

- **C3.1** Absent, present-null, and present-value MUST be distinguished wherever the contract declares partial input.
- **C3.2** A representation that cannot express a required distinction MUST be rejected, or mapped through an explicitly selected policy.
- **C3.3** A generator MUST reject a default whose phase is not declared.
- **C3.4** A decoding default MUST NOT become a business default or database default.
- **C3.5** An explicit null MUST NOT be replaced by an inferred default, and MUST NOT be changed except by a normalization policy selected for that property.
- **C3.6** A generator MUST reject a selected normalization policy that it does not support.
- **C3.7** A normalization policy MUST NOT turn present-null into absent or into a business default.

## C4. Constraints and business decisions

Examples: none yet: the scenarios of the Shipment example follow in a later slice.

- **C4.1** A generator MUST diagnose or reject a constraint that affects correctness and that it does not support. It MUST NOT present partial validation as complete.
- **C4.2** Client-side validation and generated guards MUST NOT be presented as server-side authorization.
- **C4.3** Where an operation needs a business decision, generated code MUST invoke authored code through a declared seam and MUST NOT embed, replace or bypass that decision. Where no business decision is needed, generated code MUST NOT invent one.

## C5. Validation, configuration, and diagnostics

Examples: test contracts [`invalid/fragment-include-empty/`](../examples/contracts/invalid/fragment-include-empty/), [`invalid/fragment-include-string/`](../examples/contracts/invalid/fragment-include-string/), [`invalid/fragment-version/`](../examples/contracts/invalid/fragment-version/), [`invalid/integer-overflow.yaml`](../examples/contracts/invalid/integer-overflow.yaml), [`invalid/unknown-key.yaml`](../examples/contracts/invalid/unknown-key.yaml), [`invalid/unsupported-version.yaml`](../examples/contracts/invalid/unsupported-version.yaml).

- **C5.1** Metadata MUST keep enough provenance for actionable diagnostics.
- **C5.2** Contradictory or ambiguous mappings MUST fail, unless an explicit resolution policy is declared.
- **C5.3** A generator MUST diagnose contradictions between authoritative sources instead of letting one redefine another.
- **C5.4** Generator configuration MAY refine inferred behavior, but MUST NOT weaken the authoritative public contract.
- **C5.5** A generator MUST NOT report success when a required generation stage failed.
- **C5.6** A generator MAY generate in several stages, but MUST report overall failure and protect authored code.
- **C5.7** A generator MUST reject an unsupported contract or configuration version before generating anything that depends on it. It MUST NOT reinterpret it as a supported version.
- **C5.8** Unknown keys in the contract or configuration MUST be diagnosed and MUST NOT fall back to default behavior. Extension keys (`x-` in the contract) are exempt.
- **C5.9** A generator MUST document for its generator configuration: the layer order, how scalars, maps, and lists merge, the difference between an omitted value and explicit null, how entries are removed or that removal is unsupported, and the base for relative paths.
- **C5.10** The effective configuration MUST follow the declared precedence and merge rules. Ambiguous declarations at the same priority MUST fail. Provenance MUST identify the winning declaration.
- **C5.11** A generator MUST use the standard diagnostic identifiers for contract validation (K1.10), MUST document its own diagnostic severities and stable diagnostic identifiers, and MUST distinguish generation rejection from execution failure and warnings from errors.
- **C5.12** A generator MUST report severity, identifier, and provenance as it documents them, and MUST NOT report a run with an error as successful.

## C6. Generation and extension

Examples: none yet: the scenarios of the Shipment example follow in a later slice.

- **C6.1** The same contract, configuration, and toolchain MUST produce the same owned output set with the same behavior on every run.
- **C6.2** The same contract, configuration, and toolchain SHOULD produce byte-identical output.
- **C6.3** A generator MUST document the runtime dependencies of its generated code.
- **C6.4** Generated code MUST NOT need the generator or its analyzer at runtime.
- **C6.5** Annotations or other compile-time metadata MUST NOT pull in the generator or analyzer as a dependency.
- **C6.6** A generated component MUST have a documented seam for customizing or replacing it.
- **C6.7** A replacement MUST NOT coexist with the generated component as a conflicting duplicate registration.

## C7. Independence

Examples: none: these requirements apply to the specification itself.

- **C7.1** The specification MUST NOT require a runtime class model, framework, entity base class, transport protocol, or CRUD pattern.
- **C7.2** Profiles MUST NOT require a specific runtime library; each generator chooses its own.

## C8. Authoring and strategies

Examples: none yet: the scenarios of the Shipment example follow in a later slice.

- **C8.1** An exporter MUST produce a contract that is valid against the JSON Schema and complete for the profiles it exports: every element generated code depends on is present.
- **C8.2** Exporting code generated from a contract MUST yield a contract with the same meaning for the profiles involved.
- **C8.3** A generator MUST reject a contract that selects a strategy it does not support. It MUST NOT substitute another strategy.
- **C8.4** Where two generated components depend on a convention to work together, the convention MUST come from the contract or this specification, never from the generator or framework alone.

## Rationale

- **Presence separate from nullability (C3).** "Not sent" and "sent as null" mean "leave unchanged" and "clear" in a partial update. Most languages collapse both into null, so the contract has to say where the difference matters.
- **Normalization only per property, from a closed list (C3.5, C3.6).** A global "null becomes empty list" silently changes meaning in every layer; a per-property choice is visible and reviewable.
- **Behavioral, not byte, determinism as MUST (C6.1, C6.2).** Byte-identical output is desirable for diffs and caching, but timestamps or formatter versions should not make a generator non-conformant.
- **Generator configuration layering belongs to generators (C5.9).** Build tools differ per stack; the contract itself is a single document and needs no layering.
- **Strategies instead of one convention (C8.3, C8.4).** Pagination, filter syntax, and error formats differ between good frameworks. Making the choice explicit keeps Rialto open and every contract unambiguous.
- **Round-trip export (C8.2).** Code-first and contract-first teams must be able to share one contract; that only works if neither direction loses meaning.
- **No runtime library required (C7.2).** A contract must be usable with any framework; a generator may target a library, but the specification never does.
