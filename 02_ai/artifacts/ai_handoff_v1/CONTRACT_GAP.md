# AI Handoff v1 Contract Gap

## Release Bundle

`02_ai/contracts/bundle_manifest.schema.json` does not exist in the current
repository. No `scripts/build_release.py` or release-bundle builder was found.

The only manifest-like file found outside source manifests is:

- `02_ai/data/processed/financial_synthetic/manifest.json`

That file is a dataset manifest, not a BE release bundle manifest. It is not
used as a release bundle schema.

## Decision

No release bundle manifest is generated in this step.

Current generated files stop at:

```text
EVAL-AI-001..004
-> PE-AI-CUSTOMER-SUPPORT-001
-> WPB-AI-CUSTOMER-SUPPORT-001
-> RDC-AI-CUSTOMER-SUPPORT-001
```

## Required Additional Contract

To build a release bundle, the repository needs one explicit bundle manifest
contract or builder input.
