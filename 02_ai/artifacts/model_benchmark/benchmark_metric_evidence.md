# Benchmark Metric Evidence

## Evaluation Framework

This is a NIST AI RMF / TEVV-aligned operational evaluation, not a generic model leaderboard or independent conformity assessment. The eight metrics were operationalized by FPG; no source is represented as prescribing this exact set.

## NIST AI RMF

AI RMF 1.0 (2023-01-26) supplies the Valid & Reliable, Safe, Secure & Resilient, Accountable & Transparent characteristics and the GOVERN/MAP/MEASURE/MANAGE structure. MEASURE calls for appropriate metrics, repeatable TEVV, uncertainty, benchmark comparison and documented results. NIST states that AI RMF 1.0 is under revision as of 2026-09-12, so this benchmark records 1.0 as its versioned basis rather than anticipating the revision.

## NIST Generative AI Profile

NIST AI 600-1 (2024-07-26, final) is the cross-sector companion profile used for generative-model risk measurement, deployment-context analysis and monitoring.

## NIST TEVV-Athlon

NIST AI 200-2 was an Initial Public Draft announced 2026-08-07 with comments open through 2026-10-06. It is only a supporting reference. Its extensible, adaptable and use-case-specific evaluation framing informs the repeated synthetic case design.

## MLPerf / MLCommons

MLPerf supplies industry terminology for end-to-end latency, percentiles, TTFT, TPOT/TBT and tokens per second. This harness is not an MLPerf submission; non-streaming provider calls expose E2E latency and token usage, while TTFT remains N/A.

## Peer-reviewed references

HELM motivates transparent multi-metric evaluation and trade-off reporting. CheckList motivates stratified capability-oriented behavioral cases beyond one aggregate accuracy measure.

## 8-Metric Crosswalk

See `benchmark_metric_crosswalk.csv`.

## Limitations

- NIST does not prescribe these exact eight metrics.
- The metrics operationalize NIST principles for this frozen FPG financial workload.
- Token and cost are operational-efficiency measures; cost is N/A without verified official per-model API Trial prices.
- Policy Compliance measures model behavior against field/output constraints, not Production E2 provider authorization.
- TEVV-Athlon is an Initial Public Draft, not a final standard.
- Provider non-streaming metadata does not expose TTFT or TPOT.
- The 30 cases are model-selection data and must not be reused as hold-out data.
