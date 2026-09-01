# Financial Synthetic Dataset Snapshot

This directory contains the processed `financial_synthetic` dataset snapshot for 04 Experiment reproducibility.

## Lineage

Source Dataset -> Jupyter Cleaning -> `data/processed/financial_synthetic` Dataset Snapshot -> 04 Experiment -> Validation Artifact -> Gateway Policy Candidate validation

Cleaning Notebook: `NOT_LINKED`

The cleaning notebook path is not linked because no repository notebook for the `financial_synthetic` cleaning step was found.

## Scope

- Dataset stage: processed
- Dataset version: financial_synthetic_processed_v1
- Schema version: v1
- Source type: synthetic
- Preprocessing: missing-value handling and duplicate handling completed in Jupyter
- Intended use: input dataset snapshot for 04 Experiment design, evaluation, and result reproducibility

## Runtime Database Handoff

ADP-BE owns runtime database integration separately:

- Flyway migration = PostgreSQL schema management
- Dataset import/seed loader = load a designated dataset version into PostgreSQL

This ADP-DA snapshot does not include PostgreSQL migrations, bulk INSERT SQL, runtime DB loading, Gateway Policy changes, threshold decisions, or transform outputs.
