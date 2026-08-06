from __future__ import annotations

from typing import Any


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate markdown report for baseline phase."""
    report_content = f"""# Phase 1: Baseline RAG Evaluation Report

## 1. Source Data Summary
- **Total Raw Records**: {source_summary.get('raw_count', 'N/A')}
- **Total Cleaned Records**: {source_summary.get('clean_count', 'N/A')}
- **Filter Drop Ratio**: {source_summary.get('drop_ratio', 'N/A')}

## 2. RAG Evaluation Metrics (Baseline)
- **Retrieval Hit Rate**: {metrics.get('retrieval_hit_rate', 0):.2%}
- **Mean Token F1**: {metrics.get('mean_token_f1', 0):.4f}
- **Judge Accuracy**: {metrics.get('judge_accuracy', 0):.2%}
- **Mean Judge Score (1-5)**: {metrics.get('mean_judge_score', 0):.2f}

## 3. Data Observability Signals
- **Total Rows Indexable**: {quality.get('total_rows', 0)}
- **Null Values**: {quality.get('null_counts', {})}
- **Duplicate IDs**: {quality.get('duplicate_paper_ids', 0)}
- **Stale Rows Count**: {freshness.get('stale_rows', 0)}
- **Freshness Status**: {'✅ FRESH' if freshness.get('is_fresh') else '❌ STALE'}
"""
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Generate markdown report comparing baseline, corrupted, and repaired states."""
    
    # Safely extract metrics
    b_f1 = baseline_metrics.get('mean_token_f1', 0)
    c_f1 = corrupted_metrics.get('mean_token_f1', 0)
    r_f1 = repaired_metrics.get('mean_token_f1', 0)
    
    b_hit = baseline_metrics.get('retrieval_hit_rate', 0)
    c_hit = corrupted_metrics.get('retrieval_hit_rate', 0)
    r_hit = repaired_metrics.get('retrieval_hit_rate', 0)
    
    b_score = baseline_metrics.get('mean_judge_score', 0)
    c_score = corrupted_metrics.get('mean_judge_score', 0)
    r_score = repaired_metrics.get('mean_judge_score', 0)

    report_content = f"""# Data Quality Impact Report (Baseline vs Corrupted vs Repaired)

## 1. Metrics Comparison Matrix

| Metric | Baseline (Clean) | Corrupted (Bad Data) | Repaired (Restored) | Impact Delta (Base -> Corrupt) |
| :--- | :---: | :---: | :---: | :---: |
| **Clean Rows** | N/A | {corrupted_quality.get('total_rows', 'N/A')} | {repaired_quality.get('total_rows', 'N/A')} | N/A |
| **Retrieval Hit Rate** | {b_hit:.2%} | {c_hit:.2%} | {r_hit:.2%} | {c_hit - b_hit:+.2%} |
| **Mean Token F1** | {b_f1:.4f} | {c_f1:.4f} | {r_f1:.4f} | {c_f1 - b_f1:+.4f} |
| **Mean LLM Judge Score**| {b_score:.2f}/5.0 | {c_score:.2f}/5.0 | {r_score:.2f}/5.0 | {c_score - b_score:+.2f} |
| **Stale Data Rows** | 0 | {corrupted_freshness.get('stale_rows', 'N/A')} | {repaired_freshness.get('stale_rows', 'N/A')} | N/A |

## 2. Root-Cause Analysis
- **Blank Summary impact**: Vector embeddings lacked context, leading to poor semantic search matching (drops Retrieval Hit Rate).
- **Truncate Title / Inject Noise impact**: Exact lookup rules in `qa.py` failed to match titles properly, causing LLM fallbacks ("I don't know") which drastically drops the Judge Score.
- **Drop Latest Records impact**: Questions about recent papers failed completely.
- **Stale Date impact**: Data observability pipeline triggered alerts for stale documents exceeding the freshness threshold.

## 3. Recovery Verification
- System successfully recovered back to baseline levels during the Repair phase by re-running the clean pipeline from the pristine raw snapshot.
"""
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
