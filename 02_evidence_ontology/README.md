# Evidence Ontology Module

This module preserves official regulatory and policy evidence for Financial Privacy Gateway.

The layer boundary is strict:
- Evidence: official source text and directly extractable control candidates.
- Gateway Rule: not generated in this module.
- Transform Engine: implementation methods such as masking, HMAC pseudonymization, or vault tokenization are not represented as legal evidence.

Final outputs:
- `raw/official_sources/official_sources_manifest.json`
- `processed/evidence_master.json`
- `processed/evidence_master.csv`
- `processed/evidence_ontology.json`
- `review/review_required.json`
- `review/validation_report.json`

Coverage:
- `PRIVACY`: privacy, pseudonymization, outsourcing, third-party transfer, cross-border transfer, re-identification, additional information separation, retention/logging.
- `AI`: financial AI guideline evidence, external AI use, input/output privacy controls, model data reuse checks.
- `SAAS_CLOUD`: electronic financial supervision, SaaS/cloud, network separation exceptions, monitoring, logs, access control, encryption.
- `DIGITAL_ASSET`: virtual asset laws, AML/CFT official evidence, virtual asset transfer information, wallet address evidence.

Rules:
- Use official sources only.
- Preserve `original_text` as source of truth.
- Do not infer legal conclusions that are absent from source text.
- Do not mark `REVIEW_REQUIRED` as `VERIFIED` automatically.
- Do not create `policy_rules.json`.
