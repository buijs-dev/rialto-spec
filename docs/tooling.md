# Tooling

This page lists the tooling that implements the Rialto specification. It is informative: what a tool must do is
defined in the [specification](../spec/overview.md).

Everything needed to read and validate a contract is in this repository: the [contract format](../spec/contract.md)
with its [JSON Schema](../spec/contract-1.0.0.schema.json) and the [shared test contracts](../examples/contracts/README.md).
Anyone may build tooling or generators for it.

## Reference implementations

The owner develops these alongside the specification, slice by slice:

- [rialto-jvm](https://github.com/buijs-dev/rialto-jvm): tooling for JVM projects, with a typed contract model and a
  command-line tool.
- [rialto-dart](https://github.com/buijs-dev/rialto-dart): the same for Dart and Flutter.

In slice 0 both bring loading, validation (`validate`) and bundling (`bundle`) of contracts, with the
[standard diagnostic codes](../spec/contract.md#standard-diagnostic-codes). The rest of this page, with generators,
the registry and how to write a generator, follows with the slices that bring them.
