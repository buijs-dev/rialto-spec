# Types

Every property of a contract has a type: a built-in type, a collection, or a type declared under `types`. This guide
explains the types of the contract format, the one JSON form each has, and what a tool rejects. It is for contract
authors and for builders of Rialto tooling. It is informative: the rules are those of
[K2](../../spec/contract.md#k2-types) and the section [Types](../../spec/contract.md#types), and this guide cites them
rather than repeating them.

## Why

A backend and a frontend only agree on a value if they agree on its text. Amounts of money and identifiers break
silently when a JSON parser turns them into doubles. "09:00 in Amsterdam", "09:00+01:00" and "08:00Z" are different
facts once daylight saving time changes.

The types of the contract format give every value one JSON representation, with four properties:

- **One form per type.** The forms are those of existing standards: RFC 3339, RFC 9557, ISO 8601, RFC 4648 and
  RFC 8259.
- **Exact values.** An `int64` or a `decimal` never passes through binary floating point (K2.1). A `decimal(p,s)` value
  that does not fit is rejected, not rounded (K2.2).
- **No implicit conversions.** An `instant`, an `offsetDateTime` and a `zonedDateTime` are different types, and the
  local types `date`, `time` and `localDateTime` are not points in time (K2.3, K2.4).
- **Alternatives that can be decoded.** An enum is closed or extensible (K2.7); a union names its variant in a
  discriminator (K2.8).

## How it works

### Built-in types

| Type | Values | JSON representation |
|---|---|---|
| `boolean` | true, false | `true`, `false` |
| `int32`, `int64` | signed integers of that width | number; an `int64` may be a string where OpenAPI says so |
| `decimal`, `decimal(p,s)` | exact decimal number, optionally with at most `p` digits of which `s` after the point | number or string, as OpenAPI says |
| `float64` | IEEE 754 binary64, without NaN and infinities | number |
| `string` | Unicode text | string |
| `uuid` | UUID (RFC 9562) | string, lowercase on output |
| `date` | calendar date | `2026-10-31` |
| `time` | local time of day | `09:30:00` |
| `localDateTime` | date and time without offset or zone | `2026-10-31T09:30:00` |
| `instant` | point in time | RFC 3339 `date-time`, written in UTC with `Z` |
| `offsetDateTime` | point in time with its UTC offset | `2026-10-31T09:30:00+01:00` |
| `zonedDateTime` | point in time in a named time zone | `2026-10-31T09:30:00+01:00[Europe/Amsterdam]` |
| `duration` | exact amount of time | days, hours, minutes and seconds only: `P1DT2H30M` |
| `period` | calendar amount | years, months and days only: `P1Y2M10D` |
| `bytes` | binary data | base64 |
| `json` | any JSON value, not interpreted | the value itself |
| `binary` | a stream of bytes with a media type, such as a photo or a PDF | none: a whole request or response body, or a part of `multipart/form-data` |

The full table, with the standard behind each form, is in [Types](../../spec/contract.md#types). An OpenAPI document
may only narrow a form, for example by sending an `int64` as a string.

### Type expressions

The `type` of a property is a type expression:

| Expression | Meaning |
|---|---|
| `string`, `decimal(8,3)`, … | a built-in type |
| `Shipment` | a type declared under `types`; a name starts with an uppercase letter |
| `list<T>` | ordered elements |
| `set<T>` | unique elements |
| `map<K, V>` | `K` is `string`, `uuid`, `int32`, `int64`, `date` or an enum |
| `list<T?>`, `set<T?>`, `map<K, V?>` | the elements or values may be null |

- **One level.** The element, key and value of a collection are a built-in type or a named type. Collections of
  collections are not supported in this version.
- **Map keys.** A key is written as its JSON string form when it is used as an object key.
- **Nullability.** A `?` belongs after a type argument only. Whether a property itself may be null is its own key,
  `nullable` (default false). Whether it may be absent is a property of a shape or operation, declared separately
  ([C3.1](../../spec/core.md#c3-presence-nullability-and-defaults)).

```yaml
types:
  Parcel:
    kind: entity
    identity: [id]
    properties:
      id: {type: uuid}
      weight: {type: "decimal(8,3)"}
      tags: {type: "set<string>"}
      notes: {type: "list<string?>"}
      labels: {type: "map<string, string>"}
      deliveredAt: {type: instant, nullable: true}
```

### Named types, enums and unions

Named types are declared under `types` with a `kind`: `entity`, `value`, `enum`, `union` or `projection`.

```yaml
types:
  PaymentMethod: {kind: enum, members: [card, invoice], extensible: true}
  Payment:
    kind: union
    discriminator: method
    variants: {card: CardPayment, invoice: InvoicePayment}
```

- **An enum** lists its `members`. A closed enum rejects any other value. An enum with `extensible: true` keeps a value
  that is not a member, and generated code tells it apart from the declared members (K2.7).
- **A union** is one of its `variants`. Per variant, the key is the value of the `discriminator` property on the wire.
  Encoding writes that value; decoding selects the variant by it and rejects an unknown value (K2.8). A variant need
  not declare the discriminator as a property; when it does, its type is `string`.

### Constraints

A property can carry constraints such as `maxLength`, `minimum` or `pattern`, with the semantics of JSON Schema
validation. A `binary` declares `maxSize`, and optionally `mediaTypes`. A `json` value has no constraints (K2.10). The
full list is in [Types](../../spec/contract.md#types).

## Scenarios

| You want to model | Use | On the wire |
|---|---|---|
| An amount of money | `decimal(p,s)` | a number or string, as OpenAPI says; never through binary floating point (K2.1) |
| An identifier that needs 64 bits | `int64` | a number, or a string where OpenAPI says so (K2.1) |
| A number with IEEE 754 semantics | `float64` | a number; never NaN or infinite (K2.9) |
| A point in time | `instant` | `date-time` in UTC with `Z` (K2.3) |
| A point in time with its UTC offset | `offsetDateTime` | `2026-10-31T09:30:00+01:00`, offset kept (K2.3) |
| A point in time in a named time zone | `zonedDateTime` | `2026-10-31T09:30:00+01:00[Europe/Amsterdam]`, zone kept (K2.3) |
| A calendar date, a local time of day | `date`, `time` | `2026-10-31`, `09:30:00` |
| A date and time without offset or zone | `localDateTime` | `2026-10-31T09:30:00` |
| An exact amount of time | `duration` | `P1DT2H30M` |
| A calendar amount | `period` | `P1Y2M10D` |
| Binary data inside a JSON value | `bytes` | base64 |
| A stream of bytes with a media type, such as a photo or a PDF | `binary` | not JSON: a whole body, or a part of `multipart/form-data` (K2.11) |
| Data without a schema of its own, such as the raw response of another system | `json` | the same JSON value (K2.10) |
| A fixed set of values that gains members over time | an enum with `extensible: true` | an unknown member is preserved (K2.7) |
| One of several types | a union with a `discriminator` | the variant's value in the discriminator property (K2.8) |
| Values by key | `map<K, V>` | a JSON object; each key in its JSON string form |

## Edge cases

### In the contract

| Situation | What happens |
|---|---|
| A type names no declared type: `owner: {type: Person}` | `RIALTO-K004` ([`invalid/unknown-type.yaml`](../../examples/contracts/invalid/unknown-type.yaml)). |
| A map key is a named type that is not an enum: `map<Point, string>` | `RIALTO-K006` ([`invalid/map-key.yaml`](../../examples/contracts/invalid/map-key.yaml)). |
| A map key is a built-in type that is not allowed: `map<boolean, string>` | `RIALTO-K006`. |
| A `decimal(p,s)` with more digits after the point than in total: `decimal(2,3)` | `RIALTO-K006`. |
| A collection of collections: `list<list<string>>` | `RIALTO-K006` ([`invalid/type-expression.yaml`](../../examples/contracts/invalid/type-expression.yaml)). |
| A `?` on the type itself: `string?` | `RIALTO-K006`. Write `nullable: true`. |
| A `binary` as an element or map value: `list<binary>`, `map<string, binary>` | `RIALTO-P021` (K2.11, [`invalid/binary-in-list.yaml`](../../examples/contracts/invalid/binary-in-list.yaml)). |
| A `binary` without `maxSize`, as a query field, or in a type or shape an operation carries as JSON | `RIALTO-P021` (K2.11). |
| An integer in the contract above 2147483647, such as `maxLength: 99999999999999` | The JSON Schema limits counts such as `minLength`, `maxLength`, `minItems`, `maxItems` and `maxSize` to 32-bit integers: `RIALTO-K002` ([`invalid/integer-overflow.yaml`](../../examples/contracts/invalid/integer-overflow.yaml)). |
| A `json` property as a query field | `RIALTO-P003` (K2.10). |
| A union variant declares the discriminator with a type other than `string`, or two variants share a discriminator value | `RIALTO-P012` (K2.8). |
| A union with one variant, or an enum without members or with a member twice | The JSON Schema requires at least two variants and at least one member, each once: `RIALTO-K002`. |
| Union variants that mix entities and value objects, or a variant that is a union | `RIALTO-P002`. |

### In values

| Situation | What happens |
|---|---|
| A `decimal(p,s)` value with too many digits | Rejected with code `precision`; never rounded (K2.2). |
| An `int64` or `decimal` value that is a JSON number | Represented exactly, not through binary floating point (K2.1). |
| A `float64` that is NaN or infinite | Never produced; encoding one fails (K2.9). |
| A `duration` with years or months, a `period` with hours | Rejected (K2.5). |
| An `instant` is written | Always in UTC with `Z` (K2.3). |
| A `date` or `localDateTime` turned into a point in time | Only with a declared time zone (K2.4). |
| A value of a closed enum that is not a member | Rejected (K2.7). |
| A value of an extensible enum that is not a member | Preserved through decoding and encoding, and distinguishable from the members (K2.7). |
| A union value with an unknown discriminator value | Rejected (K2.8). |
| A `json` value is decoded and encoded again | The same JSON value: numbers keep their exact value, no member is added or dropped (K2.10). |
| A `pattern` on a platform whose regular expressions differ from ECMA-262 | Translated faithfully, or rejected by the generator (K2.6). |

## Design decisions

From the [rationale](../../spec/contract.md#rationale) of the specification:

- **One JSON form per type (K2).** A backend and a frontend only agree on a value if they agree on its text. RFC 3339,
  RFC 9557, ISO 8601 and RFC 4648 already define these forms.
- **An uninterpreted `json` type (K2.10).** Some data, such as the raw response of another system kept for later
  processing, has no schema of its own. A typed contract can only carry it as opaque JSON, and saying so is better
  than a string with JSON inside.
- **Exact numbers (K2.1, K2.2).** Amounts of money and identifiers break silently when a JSON parser turns them into
  doubles. Rounding hides the error instead of reporting it.
- **Instant, offset, zone and local time are different types (K2.3, K2.4).** "09:00 in Amsterdam", "09:00+01:00" and
  "08:00Z" are different facts once daylight saving time or a meeting place changes. Converting implicitly loses the
  difference.
- **Extensible enums (K2.7).** A client released before a new member was added must keep working. Preserving the
  unknown value is what makes adding members a compatible change.
- **Unions with a discriminator (K2.8).** It is how OpenAPI (`oneOf` with `discriminator`) and most languages (sealed
  types) express alternatives; decoding by trial is ambiguous. The discriminator belongs to the union and the wire,
  not to the variants: in Kotlin and Dart the variant's class already is the distinction.
- **Type expressions checked by the tool, not the schema (K1.7, K2.1).** A schema pattern can only say that a type is
  wrong; the tool can say why, with `RIALTO-K006` or `RIALTO-P021` at the property, and report the other findings of
  the contract in the same run.

## Requirements

| Requirement | In short |
|---|---|
| [K2.1](../../spec/contract.md#k2-types) | Every scalar value exactly; `int64` and `decimal` never through binary floating point |
| [K2.2](../../spec/contract.md#k2-types) | A `decimal(p,s)` value that does not fit is rejected with `precision`, not rounded |
| [K2.3](../../spec/contract.md#k2-types) | `instant` in UTC with `Z`; offset and zone kept; no conversion between them unless declared |
| [K2.4](../../spec/contract.md#k2-types) | Local types to or from a point in time only with a declared time zone |
| [K2.5](../../spec/contract.md#k2-types) | No years or months in a `duration`, no time in a `period` |
| [K2.6](../../spec/contract.md#k2-types) | `pattern` translated faithfully from ECMA-262, or rejected |
| [K2.7](../../spec/contract.md#k2-types) | A closed enum rejects non-members; an extensible enum preserves them |
| [K2.8](../../spec/contract.md#k2-types) | Distinct discriminator values; encode and decode by the discriminator |
| [K2.9](../../spec/contract.md#k2-types) | No NaN or infinite `float64` |
| [K2.10](../../spec/contract.md#k2-types) | A `json` value passes through unchanged; no constraints; not a query field |
| [K2.11](../../spec/contract.md#k2-types) | A `binary` has `maxSize`, is not in a collection, map value or query field, and is not carried as JSON |

| Code | Meaning |
|---|---|
| `RIALTO-K002` | The contract violates the JSON Schema, such as a type that is not a string or an integer above 2147483647 |
| `RIALTO-K004` | A type names no declared type |
| `RIALTO-K006` | Invalid type expression, such as an unknown scalar, a nested collection, `?` outside a collection, or a map key that is not an allowed scalar or enum |
| `RIALTO-P002` | Union variants mix entities and value objects, or a variant is a union |
| `RIALTO-P003` | A query field is `json`, or otherwise not a supported field |
| `RIALTO-P012` | A union variant declares the discriminator with a type other than `string`, or variants share a discriminator value |
| `RIALTO-P021` | A `binary` without `maxSize`, in a collection or map value, as a query field, or carried as JSON |

All codes are in the [standard diagnostic codes](../../spec/contract.md#standard-diagnostic-codes).
