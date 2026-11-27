# Tooling

This page lists the tooling that implements the Rialto specification. It is informative: what a tool must do is
defined in the [specification](../spec/overview.md).

Everything needed to read and validate a contract is in this repository: the [contract format](../spec/contract.md)
with its [JSON Schema](../spec/contract-1.0.0.schema.json) and the [shared test contracts](../examples/contracts/README.md).
Anyone may build tooling or generators for it.

The guides explain a feature in depth: why it exists, what a tool does in each situation, its edge cases and its
design decisions. They cite the requirements rather than repeat them.

- [Validation and diagnostics](guides/validation-and-diagnostics.md)
- [Contracts over several files](guides/contracts-over-several-files.md)
- [Sources and references](guides/sources-and-references.md)
- [Remote sources and the lock](guides/remote-sources.md)
- [Types](guides/types.md)

## Reference implementation

The owner develops [rialto-jvm](https://github.com/buijs-dev/rialto-jvm) alongside the specification, slice by slice:
the command-line tool `rialto`, a Gradle plugin, and a library with a typed contract model.

In slice 0 it brings loading, validation (`rialto validate`) and bundling (`rialto bundle`) of contracts, with the
[standard diagnostic codes](../spec/contract.md#standard-diagnostic-codes).

## Conformance

`rialto conformance` runs a command once per [shared test contract](../examples/contracts/README.md) and reports
which it passes. The command can be any tool, in any language:

```sh
rialto conformance --spec <checkout of this repository> -- <your tool> validate {contract}
```

A valid test contract passes when the command exits with `0`. An invalid one passes when the command exits with
another status and its output names every code in the `# expect: RIALTO-…` lines of the test contract.

The rest of this page, with generators, the registry and how to write a generator, follows with the slices that
bring them.
