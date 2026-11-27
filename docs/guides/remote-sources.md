# Remote sources and the lock

A contract can build on a document another team publishes, such as the OpenAPI document of an API it calls. This
guide explains how such a remote source is pinned in the lock of the contract, what a tool does in each situation, and
why it works this way. It is for contract authors and for builders of Rialto tooling. It is informative: the rules are
those of [K4](../../spec/contract.md#k4-remote-sources), and this guide cites them rather than repeating them.

## Why

A source at an `https` URL can change at any moment, without a change in the repository of the contract. Without a pin,
the same commit builds against one version of the document today and another tomorrow. A breaking change upstream then
shows up as a failure in an unrelated build, or worse, as generated code that silently no longer matches the reviewed
contract.

The lock records which version of every remote source was accepted: the SHA-256 of its content. It is committed with
the contract. That gives three properties:

- **Reproducible builds.** Every build reads exactly the document that was reviewed and committed (K4.1).
- **Visible upstream changes.** When the document changes, the build fails with `RIALTO-S004` until someone accepts
  the new version on purpose. The new hash then shows up as a diff in a pull request (K4.2).
- **Offline builds.** The cache keeps documents by hash, so a build with a lock and a filled cache needs no network
  (K4.3).

## How it works

```yaml
# shipment.rialto.yaml
rialto: "1.0.0"
info: {name: shipment, version: 2.0.0}
sources:
  catalog: {kind: openapi, path: "https://catalog.example.com/openapi.json", version: 3.1.0, status: current}
```

```yaml
# shipment.rialto.lock
contract: shipment.rialto.yaml
sources:
  "https://catalog.example.com/openapi.json": "3f2a…9c1e"
```

- **The lock** lies next to the root of the contract and is named after it: `shipment.rialto.lock` for
  `shipment.rialto.yaml` or `shipment.yaml` (K4.6). It names the root it belongs to under `contract` (K4.7). It holds
  one hash per URL, in lowercase hexadecimal.
- **The cache** keeps every fetched document by its hash, outside the repository. A document in the cache with the
  pinned hash is the pinned version; no network is needed to read it.
- **Three modes.** A normal run reads pinned sources and pins new ones. An offline run reads only the cache. An update
  (`rialto sources update`) fetches every remote source again and pins what upstream serves now.
- **Only `https`** (K4.4). A redirect from `https` to `http` is not followed.

## Scenarios

### A normal run

| Situation | What the tool does | Diagnostic |
|---|---|---|
| The source is pinned and the cache has that hash | Reads the cached copy, without fetching | — |
| The source is pinned, the cache does not have it | Fetches it and compares the hash; reads it when equal | `RIALTO-S004` when it differs |
| The source is not in the lock yet | Fetches it and adds its hash to the lock (K4.1) | — |
| The lock has a URL the contract no longer uses | Removes that entry from the lock | — |
| The source can be neither fetched nor found in the cache | Rejects it; never falls back to another version (K4.3) | `RIALTO-S003` |
| The run has any error, also one unrelated to sources | Writes nothing to the lock | the error itself |

### An offline run

| Situation | What the tool does | Diagnostic |
|---|---|---|
| The source is pinned and cached | Reads the cached copy | — |
| The source is pinned but not cached | Rejects it | `RIALTO-S003` |
| The source is not in the lock | Rejects it: there is no pin to check a copy against | `RIALTO-S003` |
| Any situation | Never writes the lock | — |

### An update

| Situation | What the tool does | Diagnostic |
|---|---|---|
| Every source can be fetched | Pins the current hash of each, reports `url: before -> after` per change | — |
| One source cannot be fetched | Leaves the whole lock as it was | `RIALTO-S003` |

An update is the only way a pinned hash changes (K4.2).

## Edge cases

| Situation | What happens |
|---|---|
| The lock exists but cannot be read: a directory, invalid YAML, not a mapping, a hash that is not a SHA-256 | `RIALTO-K010`, naming the lock and the sources left unpinned. The remote sources are not fetched. The other findings of the run are still reported. The lock is never taken as empty (K4.5): that would silently pin whatever upstream serves now. |
| The lock is empty, or holds only comments | An empty lock; valid. |
| The lock must change but cannot be written | `RIALTO-K010` for a new or changed hash. When the run would only remove unused entries, the lock is left as it is; that can wait for the next run. |
| Two contracts in one directory | Each has its own lock (K4.6). A build of one never removes the pins of the other. |
| `shipment.yaml` and `shipment.rialto.yaml` in one directory | Both have `shipment.rialto.lock`. The lock names the first one that wrote it; the other gets `RIALTO-K010` (K4.7). Rename one of them. |
| Two roots that differ only in case, on a file system that ignores case | One file on disk. The name in the lock is compared exactly, so the second gets `RIALTO-K010`. |
| A lock copied along with another contract | Its `contract` names the other root: `RIALTO-K010`, and nothing is pinned again. |
| A contract is renamed, its lock is not | The new name has no lock yet, so its sources are pinned again. That is visible in the pull request as a new lock file. Rename the lock along with the contract to keep the reviewed pins. |
| A contract over several files | One lock, next to the root and named after it. Fragments have no `sources` ([K5](../../spec/contract.md#k5-contract-over-several-files)). |
| The same URL in two contracts | Two pins, one in each lock. An update of one contract does not change the other; the other sees the new version as `RIALTO-S004` until it is updated too. |
| Whitespace or key order changes upstream | Different bytes, so a different hash: `RIALTO-S004`. The pin is on the bytes of the document, not on its meaning. |
| Two runs on the same contract at the same time, such as Gradle and the command line | They take turns on the lock, and a reader never sees a half-written file. A run that pins a source another run pinned to a different hash in the meantime gets `RIALTO-K010` and can run again. |

## Design decisions

From the [rationale](../../spec/contract.md#rationale) of the specification:

- **Pinned remote sources (K4).** A contract that refers to an API another team publishes must build the same way
  tomorrow. A hash makes an upstream change visible as a deliberate update with a diff, not a surprise in a later
  build.
- **One lock per contract, named after it (K4.6).** What a lock pins belongs to one contract. Contracts in one
  directory that shared a lock would each remove the other's entries as unused, and the next run would pin whatever
  upstream serves then, without the check of K4.2. A rule that only one contract may live in a directory could not be
  checked by a tool that is given one contract. One lock per directory with a section per contract was rejected:
  every contract would write the same file, with merge conflicts between unrelated changes.
- **The lock names its contract (K4.7).** Two roots that differ only in extension or case, or a lock copied along with
  a contract, would otherwise share a lock without anyone noticing.

Following from the requirements:

- **An unreadable lock is an error, not an empty lock (K4.5).** An empty lock would pin every source again, without
  the check of K4.2.
- **No fallback to another version (K4.3).** A source that can be neither fetched nor found in the cache with its
  pinned hash is rejected, never replaced by another copy.

## Requirements

| Requirement | In short |
|---|---|
| [K4.1](../../spec/contract.md#k4-remote-sources) | Read a remote source only when its hash equals the pin; pin a new source |
| [K4.2](../../spec/contract.md#k4-remote-sources) | Reject a changed source; change a pin only by an explicit update |
| [K4.3](../../spec/contract.md#k4-remote-sources) | Work offline from the cache; never fall back to another version |
| [K4.4](../../spec/contract.md#k4-remote-sources) | `https` only |
| [K4.5](../../spec/contract.md#k4-remote-sources) | An unreadable or unwritable lock is `RIALTO-K010`, never an empty lock |
| [K4.6](../../spec/contract.md#k4-remote-sources) | The lock is named after the root of its contract |
| [K4.7](../../spec/contract.md#k4-remote-sources) | The lock names its contract |

| Code | Meaning |
|---|---|
| `RIALTO-K010` | The lock cannot be read, belongs to another contract, or cannot be written when it must change |
| `RIALTO-S003` | A remote source can neither be fetched nor found in the cache |
| `RIALTO-S004` | A remote source differs from its hash in the lock |
| `RIALTO-S005` | A remote source does not use `https` |

All codes are in the [standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes).
