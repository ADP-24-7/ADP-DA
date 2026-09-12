# Three-Model Isolated Operational Benchmark

## 1. Purpose

Compare three models under identical synthetic financial tasks while preserving the frozen Production E1/E2/E3 baseline.

## 2. Evidence Basis

This NIST AI RMF / TEVV-aligned operational evaluation uses NIST AI RMF 1.0 and NIST AI 600-1 to ground trustworthiness and GAI measurement; the NIST AI 200-2 TEVV-Athlon Initial Public Draft is a supporting design reference; MLPerf supplies inference terminology. This is not an independent conformity assessment or an MLPerf result.

## 3. Design

30 cases × 6 workload strata × 3 models × 3 repetitions = 270 actual model executions. Inputs are synthetic and non-linkable. Temperature 0, top_p 1, 512 output tokens and JSON output are fixed.

## 4. Metrics

Quality, Latency, Token Efficiency, Cost, Stability, Policy Compliance, Format Compliance and Consistency are frozen before execution. Cost is N/A without verified official per-model API Trial pricing.

## 5. Results

| Model | Quality | Latency mean ms | p95 ms | Tokens avg | Stability % | Policy % | Format % | Consistency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron 3.5 Lightning | 80.2685 | 23611.1129 | 115338.1053 | 296.1 | 91.1111 | 65.5556 | 91.1111 | 76.2222 |
| Muse Glimmer 30B | 89.1204 | 13306.4627 | 30576.8057 | 424.3556 | 100.0 | 76.6667 | 100.0 | 87.3333 |
| Gemma 4 31B IT | 84.75 | 8838.8065 | 35231.2307 | 258.2111 | 100.0 | 61.1111 | 100.0 | 81.7778 |

### Workload Quality

| Model | Workload | Quality mean |
|---|---|---:|
| Nemotron 3.5 Lightning | simple_lookup_summary | 80.0 |
| Nemotron 3.5 Lightning | exact_numeric_processing | 84.6111 |
| Nemotron 3.5 Lightning | relationship_preservation | 72.0 |
| Nemotron 3.5 Lightning | document_rag | 93.0 |
| Nemotron 3.5 Lightning | composite_reasoning | 68.0 |
| Nemotron 3.5 Lightning | policy_format_compliance | 84.0 |
| Muse Glimmer 30B | simple_lookup_summary | 89.3333 |
| Muse Glimmer 30B | exact_numeric_processing | 83.7222 |
| Muse Glimmer 30B | relationship_preservation | 89.3333 |
| Muse Glimmer 30B | document_rag | 97.0 |
| Muse Glimmer 30B | composite_reasoning | 79.3333 |
| Muse Glimmer 30B | policy_format_compliance | 96.0 |
| Gemma 4 31B IT | simple_lookup_summary | 68.0 |
| Gemma 4 31B IT | exact_numeric_processing | 82.8333 |
| Gemma 4 31B IT | relationship_preservation | 89.3333 |
| Gemma 4 31B IT | document_rag | 97.0 |
| Gemma 4 31B IT | composite_reasoning | 83.3333 |
| Gemma 4 31B IT | policy_format_compliance | 88.0 |

## 6. Statistical Comparison

Paired Friedman tests use case × repetition blocks; Kendall's W is reported as the omnibus effect size.

| Metric | Blocks | Statistic | p-value | Kendall W |
|---|---:|---:|---:|---:|
| quality | 90 | 11.065421 | 0.0039552547 | 0.061475 |
| latency | 90 | 28.466667 | 6.585e-07 | 0.158148 |
| total_tokens | 90 | 119.150838 | 0.0 | 0.661949 |
| consistency | 30 | 4.836364 | 0.0890834402 | 0.080606 |

## 7. Trade-offs

- quality: Muse Glimmer 30B
- latency: Gemma 4 31B IT
- token: Gemma 4 31B IT
- cost: N/A
- stability: Muse Glimmer 30B; Gemma 4 31B IT
- policy: Muse Glimmer 30B
- format: Muse Glimmer 30B; Gemma 4 31B IT
- consistency: Muse Glimmer 30B

The comparison retains raw metrics; it does not claim that one model dominates every dimension.

## 8. Recommended Model

**Gemma 4 31B IT** has the highest pre-frozen weighted score over available metrics (79.9397). The cost component remains N/A and is excluded from the calculable 90% denominator; fixed weights were not changed.
The margin over the second available-metric score is 0.0914 points, so the recommendation is provisional until a new hold-out confirms it.
For each calculable metric, min-max normalization maps the observed three-model range to 0-100; lower is better for latency and tokens. The available fixed weights are then renormalized over 90%.

## 9. FPG Meaning

### Production Runtime

`ACTIVE_FAIL_CLOSED / BLOCK`

### Model Evaluation

`ISOLATED BENCHMARK HARNESS`

> Benchmark actual calls do not authorize Production External Execution.

FPG remains model-independent: it compares model behavior under common field, exactness and output constraints without altering Production E1/E2/E3.

## 10. Next

Freeze this benchmark/evidence, create a new non-overlapping hold-out dataset, and validate only the selected model.
