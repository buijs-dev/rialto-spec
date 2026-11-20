# Test contracts

Small contracts that every implementation of Rialto tooling validates the same way (K1.5, K1.7, K1.10). 
Files in `valid/` must produce no errors. 
A directory with a `contract.rialto.yaml` is a [contract over several files](../../spec/contract.md#contract-over-several-files): 
that file is the root. Each file in `invalid/`, or root of a directory there, 
names the diagnostic codes it must produce in its leading comment lines, one per line, as `# expect: RIALTO-…`; 
the codes are defined in the [standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes). `support/` holds documents the contracts refer to.

## Running the test contracts

`tools/conformance.py` runs any tool over every test contract and reports per contract whether it passed:

```sh
python3 tools/conformance.py -- rialto validate {contract}
```

```text
PASS valid/minimal.yaml
FAIL invalid/unknown-type.yaml: missing RIALTO-K004

16 passed, 1 failed; command: rialto validate '{contract}'
```

The protocol is small, so every tool can follow it:

- The command gets the absolute path of the contract, or of the root `contract.rialto.yaml` of a contract over several files, in place of `{contract}`. It runs in the directory of that file.
- A valid contract passes when the command exits with 0.
- An invalid contract passes when the command exits with another status and prints every expected code, on stdout or stderr, in any format.

`--only valid` or `--only invalid`, `--filter <text>` and `-v` (print the output of failing runs) narrow a run. A claim of conformance ([governance](../../GOVERNANCE.md#conformance)) includes the output of a complete run.

### The published test contracts

The test contracts, the JSON Schema and `spec/contract.md` are published as the zip `dev.buijs.rialto:rialto-spec` to
`https://repo.repsy.io/mvn/buijs-dev/maven` (`./gradlew publishToMavenLocal` builds it locally), at the same paths as in
this repository. The tests of an implementation unpack a pinned version of it rather than read a checkout next to theirs.

### Comparing two tools

Conformance checks that each tool reports the expected codes; two tools can still disagree on where a finding is or
which requirement it names (K1.5). `tools/compare_tools.py` runs two commands over every test contract (and, once it is
there, both forms of the Shipment example), reads their machine-readable output (`--format json`, see the
[standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes)) and reports every finding that only one
of them reports:

```sh
python3 tools/compare_tools.py --jobs 8 --a 'rialto-jvm validate --format json {contract}' \
    --b 'rialto-dart validate --format json {contract}'
```

A finding is compared by file, severity, code, pointer and requirement. `--positions` adds line and column, and
`--messages` adds message and hint, which are free text and may differ between tools. The exit status is 0 when the
tools agree on every contract.

### Capabilities and levels

Each test contract that has a contract model names what it uses in a leading `# capabilities: …` line, after its
`# expect:` lines: the capabilities and strategies, sorted, or `none`. An invalid contract that fails before a contract
model is read (a document that is not a mapping, an unknown key, an unsupported format version, a fragment that cannot
be included) has no line: what it tests is common to all tooling.

The test contracts here are those of the contract format (K) and core (C). The test contracts of each profile, and the
runner's `--level` option over the conformance levels, follow with the slice of that profile and with slice 10.
