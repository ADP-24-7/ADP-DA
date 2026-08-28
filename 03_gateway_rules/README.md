# 03 Gateway Rules

This module contains runtime Gateway Rules derived from the verified Evidence Ontology.

## Layer Boundary

- Evidence Ontology is the source and provenance layer.
- Gateway Rule is the runtime decision layer.
- Transform Engine is the implementation layer.

Gateway Rules decide only:

- `ALLOW`
- `BLOCK`
- `TRANSFORM`
- `REVIEW`
- `required_controls`
- `evidence_refs`

Gateway Rules decide whether transformation is required. They do not decide which transform technique will be used.

## Transform Engine Boundary

The following handling and comparison are reserved for the next Transform Engine layer:

- `RAW`
- `MASK`
- `HMAC-PSEUDO`
- `VAULT-TOKEN`
- `GENERALIZE`
- `FIELD-SEPARATION`

A specific transform technique is not a legal duty in this Gateway Rule layer. It is an implementation option that may be evaluated after a Gateway Rule reaches a `TRANSFORM` decision.

## Review Handling

- `VERIFIED` Evidence may support runtime `BLOCK`, `TRANSFORM`, or `REVIEW` decisions.
- `REVIEW_REQUIRED` Evidence is used only for `REVIEW` routing and never as automatic `ALLOW` or `BLOCK` support.
- Control Evidence such as `LOG`, `MONITOR`, `ENCRYPT`, `ACCESS_CONTROL`, and `SEPARATE_MAPPING` is represented in `required_controls`, not as a top-level action.
