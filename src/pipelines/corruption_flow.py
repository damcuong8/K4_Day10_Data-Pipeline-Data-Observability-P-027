from __future__ import annotations

import logging

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import load_clean_dataframe, save_clean_dataframe
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)


def _ensure_output_dirs(settings: Settings) -> None:
    paths = settings.paths
    for directory in (paths.quality_dir, paths.comparison_report.parent, paths.corrupted_metrics.parent):
        directory.mkdir(parents=True, exist_ok=True)


def _require_baseline(settings: Settings) -> dict:
    """Corruption flow chi chay sau khi baseline da tao du artifact."""
    paths = settings.paths
    missing = [str(p) for p in (paths.clean_csv, paths.eval_testset, paths.baseline_metrics) if not p.exists()]
    if missing:
        raise RuntimeError(
            "Thieu baseline artifact: " + ", ".join(missing) + "\nChay 'python script/run_phase1.py' truoc."
        )
    return read_json(paths.baseline_metrics)


def _evaluate_state(
    settings: Settings,
    df: pd.DataFrame,
    embeddings_path,
    metrics_path,
    answers_path,
    label: str,
) -> dict:
    """Build index rieng cho mot trang thai roi evaluate bang test set cu."""
    index = LocalEmbeddingIndex.build(df=df, settings=settings, embeddings_output_path=embeddings_path)
    print(f"      collection={index.collection_name}, documents={len(index.documents)}")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )
    metrics = bundle.summary
    print(f"      [{label}] hit_rate={metrics['retrieval_hit_rate']:.2%} "
          f"token_f1={metrics['mean_token_f1']:.4f} judge={metrics['mean_judge_score']:.2f}/5")
    return metrics


def main() -> None:
    """Corruption flow: corrupt -> evaluate -> repair tu raw -> evaluate -> compare."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    paths = settings.paths
    _ensure_output_dirs(settings)

    print("=" * 70)
    print("PHASE 2 - CORRUPTION / REPAIR / COMPARISON")
    print("=" * 70)

    print("\n[1/7] Load baseline artifacts...")
    baseline_metrics = _require_baseline(settings)
    baseline_df = load_clean_dataframe(paths.clean_csv)
    print(f"      baseline: {len(baseline_df)} rows, hit_rate={baseline_metrics['retrieval_hit_rate']:.2%}")

    print("\n[2/7] Corrupt clean dataset...")
    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    save_clean_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    print(f"      {len(baseline_df)} -> {len(corrupted_df)} rows, log -> {paths.corruption_log}")

    print("\n[3/7] Rebuild index + evaluate CORRUPTED...")
    corrupted_metrics = _evaluate_state(
        settings, corrupted_df, paths.corrupted_embeddings_json,
        paths.corrupted_metrics, paths.corrupted_answers, "corrupted",
    )

    print("\n[4/7] Quality + freshness tren corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    write_json(paths.quality_dir / "corrupted_quality.json", corrupted_quality)
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "freshness_report_corrupted.json"
    )
    print(f"      is_healthy={corrupted_quality['is_healthy']}, duplicates={corrupted_quality['duplicate_paper_ids']}, "
          f"stale={corrupted_quality['stale_rows_count']}")

    print("\n[5/7] Repair: chay lai cleaning tu RAW records (khong sua tay)...")
    records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, now_utc())
    save_clean_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    print(f"      repaired: {len(repaired_df)} rows tu {len(records)} raw records")

    print("\n[6/7] Rebuild index + evaluate REPAIRED...")
    repaired_metrics = _evaluate_state(
        settings, repaired_df, paths.repaired_embeddings_json,
        paths.repaired_metrics, paths.repaired_answers, "repaired",
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    write_json(paths.quality_dir / "repaired_quality.json", repaired_quality)
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "freshness_report_repaired.json"
    )

    print("\n[7/7] Comparison report...")
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"      {paths.comparison_report}")

    print("\n" + "=" * 70)
    print("SO SANH 3 TRANG THAI")
    print("=" * 70)
    header = f"{'Metric':<22}{'baseline':>12}{'corrupted':>12}{'repaired':>12}"
    print(header)
    print("-" * len(header))
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        print(f"{key:<22}{baseline_metrics.get(key, 0):>12.4f}"
              f"{corrupted_metrics.get(key, 0):>12.4f}{repaired_metrics.get(key, 0):>12.4f}")
    print(f"{'rows':<22}{len(baseline_df):>12}{len(corrupted_df):>12}{len(repaired_df):>12}")
    print(f"{'data_healthy':<22}{'-':>12}{str(corrupted_quality['is_healthy']):>12}{str(repaired_quality['is_healthy']):>12}")
