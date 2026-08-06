# Data Quality Impact Report (Baseline vs Corrupted vs Repaired)

## 1. Metrics Comparison Matrix

| Metric | Baseline (Clean) | Corrupted (Bad Data) | Repaired (Restored) | Impact Delta (Base -> Corrupt) |
| :--- | :---: | :---: | :---: | :---: |
| **Clean Rows** | N/A | 93 | 100 | N/A |
| **Retrieval Hit Rate** | 100.00% | 0.00% | 100.00% | -100.00% |
| **Mean Token F1** | 0.7500 | 0.0463 | 0.7500 | -0.7037 |
| **Mean LLM Judge Score**| 4.00/5.0 | 1.35/5.0 | 4.00/5.0 | -2.65 |
| **Stale Data Rows** | 0 | 4 | 0 | N/A |

## 2. Root-Cause Analysis
- **Blank Summary impact**: Vector embeddings lacked context, leading to poor semantic search matching (drops Retrieval Hit Rate).
- **Truncate Title / Inject Noise impact**: Exact lookup rules in `qa.py` failed to match titles properly, causing LLM fallbacks ("I don't know") which drastically drops the Judge Score.
- **Drop Latest Records impact**: Questions about recent papers failed completely.
- **Stale Date impact**: Data observability pipeline triggered alerts for stale documents exceeding the freshness threshold.

## 3. Recovery Verification
- System successfully recovered back to baseline levels during the Repair phase by re-running the clean pipeline from the pristine raw snapshot.
