# Governance

Rialto is an open specification with a single owner. This page says who decides, how the specification
changes, how versions work, and what it means to implement Rialto. It is deliberately light: the
project is young, and the rules are meant to grow with the community rather than ahead of it.

## Roles

| Role | Who | Does |
|---|---|---|
| Owner and author | Gillian Buijs ([buijs.dev](https://buijs.dev/)) | Owns the specification, makes the final decision, publishes releases |
| Maintainer | Appointed by the owner | Reviews and merges changes, triages issues |
| Contributor | Anyone | Opens issues and pull requests |
| Implementer | Anyone | Builds tooling or a generator and may claim conformance |

Today the owner is the only maintainer. A contributor who has had several changes accepted can be asked
to become a maintainer; the owner makes that decision in public, in an issue.

## Decisions

- **Benevolent owner.** The owner has the final say. The owner explains a decision that goes against
  the discussion in the issue.
- **Discuss in public.** Changes are proposed in an issue or pull request, not in private messages.
  A change that alters what a generator must do (a new or changed MUST) is open for comment for at least
  7 days before it is merged. Clarifications and fixes that do not change meaning need no waiting period.
- **Principles first.** A change is judged against the principles in the [README](README.md): an
  ambiguous or silently lossy rule is a bug, an opinionated rule belongs in a generator, not in the
  specification.

## Changing the specification

1. **Open an issue** that describes the problem, not only the solution: what two generators cannot do
   together today, or what a generator cannot express.
2. **Send a pull request** that follows [CONTRIBUTING.md](CONTRIBUTING.md): the requirement with its
   identifier, the rationale, an example, a shared test contract where a diagnostic is involved, and a
   line in the [changelog](CHANGELOG.md). `dart run tools/bin/check_spec.dart` must report OK.
3. **Review.** A maintainer reviews it. A change that affects a published profile also needs a note on
   compatibility: which existing contracts and generators it breaks, if any.
4. **Merge.** The owner or a maintainer merges. The change is part of the next release.

Identifiers of requirements are stable within a major version: a requirement is deprecated, not
renumbered or reused.

## Versions and releases

- The specification follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
  a **major** version may break contracts or generators, a **minor** version adds without breaking,
  a **patch** version clarifies without changing meaning.
- The contract format has its own version (`rialto: "1.0.0"` in a contract), which changes more slowly than
  the specification. A generator states which contract formats it reads.
- A release is a `v*` tag on `main`, with a GitHub Release that carries its changelog section.
  Implementers pin a release tag, not a branch.
- A release candidate (`1.0.0-rc.1`) may still change; from `1.0.0` on, the rules above apply in full.
- The specification is published at [rialto.buijs.dev](https://rialto.buijs.dev/), built from the `develop`
  branch; every release stays available as a tag.

## Conformance

A tool is **conformant with Rialto 1.0.0** for a profile when it satisfies the requirements of that
profile that apply to its role, and when it passes the shared test contracts in
`examples/contracts` for that profile: every valid contract is accepted, and every invalid contract is
rejected with the diagnostic codes it names. `rialto conformance` checks this for any tool
([running the test contracts](examples/contracts/README.md#running-the-test-contracts)).

- A claim names the specification version and a conformance level
  (Starter, Backend or Client) plus the capabilities beyond it, or else the profiles and capabilities, for example
  *"Acme Generator 2.1.0 implements Rialto 1.0.0: Backend + `events.consume`"* or *"Acme Mapper 1.0.0 implements
  Rialto 1.0.0: Starter (server)"*. It links to the generator's own documentation of the
  generator obligations. The conformance levels and the generator obligations are defined in Generators, which
  follows in slice 10.
- For a level, the claim includes a run of `rialto conformance --level <level>`; the option follows in slice 10.
- A claim includes the output of a complete run of `rialto conformance`, so anyone can repeat it.
- Nobody has to ask permission to claim conformance. A claim that turns out to be wrong is corrected by
  an issue, first with the implementer.
- Please use the name "Rialto" for the specification only. A tool that implements part of it says which
  part, rather than calling itself "Rialto".

## Listing implementations

Tooling and generators live in their own repositories and have their own governance. The
[tooling overview](docs/tooling.md) lists the ones the owner maintains.

A generator is listed in [rialto-registry](https://github.com/buijs-dev/rialto-registry), through a pull
request that adds its entry. The entry names the owner, the artifact and its SHA-256, the documentation of the
generator obligations, and the claim of conformance with the result of the conformance runner. CI checks the
artifact, the manifest and the claimed level; a maintainer then checks the owner and its namespaces, the claim, the
license and the obligations. Approval is not a code audit: the registry does not vouch for the code a generator
runs or generates. A version is never removed, only yanked, with a reason.

Other tooling is added to the tooling overview through a pull request that links its repository.

## Reference implementations

The owner maintains [rialto-jvm](https://github.com/buijs-dev/rialto-jvm) and the reference generators, which the
[tooling overview](docs/tooling.md) lists as they arrive. When an implementation and the specification
disagree, the specification is right, and the disagreement is filed as an issue in the repository of the
implementation. If the specification is wrong or unclear, the issue goes in this repository, and the
specification is corrected first.

## Contact and conduct

- Questions and proposals: issues and discussions in this repository.
- Security or conduct problems, or anything that should not be public: contact the owner through
  [buijs.dev](https://buijs.dev/).
- Be respectful and concrete. Comments are about the proposal, not the person. The owner can edit or
  remove comments, and block users, that break this rule.

## Licence

The specification, the examples and the tools in this repository are published under the
[Apache License 2.0](LICENSE). A contribution is made under that licence (its section 5); the licence
also grants implementers the patent rights of contributors (its section 3).

