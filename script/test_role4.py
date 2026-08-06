"""Smoke test cho Role 4 (Evaluation & Observability) tren du lieu clean THAT.

Chay doc lap, khong can phase1.py da implement xong.
Dung: uv run python script/test_role4.py
"""

from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import write_json
from evaluation.testset import build_test_set
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report, generate_phase1_report


def main() -> None:
    settings = load_settings()
    paths = settings.paths

    # Cac ham cua Role 4 dung open() tran nen khong tu tao thu muc -> tao truoc o day.
    for directory in (paths.eval_testset.parent, paths.quality_dir, paths.baseline_report.parent):
        directory.mkdir(parents=True, exist_ok=True)

    print("0. Load cleaned data that tu Role 2...")
    df = pd.read_csv(paths.clean_csv)
    print(f"   {len(df)} rows tu {paths.clean_csv}")

    print("\n1. build_test_set...")
    test_set = build_test_set(df, paths.eval_testset)
    print(f"   Tao {len(test_set)} cau hoi -> {paths.eval_testset}")
    print(f"   Sample: {test_set[0]['question']}")
    print(f"   Ground truth: {test_set[0]['ground_truth'][:80]}")

    print("\n2. run_data_quality_checks (baseline)...")
    quality = run_data_quality_checks(df, settings, "baseline_quality")
    write_json(paths.quality_dir / "baseline_quality.json", quality)
    print(f"   {quality}")
    print(f"   Ghi -> {paths.quality_dir / 'baseline_quality.json'}")

    print("\n3. build_freshness_report (baseline)...")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    print(f"   {freshness}")

    print("\n4. Kiem tra tren corrupted data (quality phai phat hien bat thuong)...")
    corrupted_df = pd.read_json(paths.corrupted_clean_json)
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    write_json(paths.quality_dir / "corrupted_quality.json", corrupted_quality)
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "freshness_report_corrupted.json"
    )
    print(f"   corrupted rows={corrupted_quality['total_rows']} (baseline={quality['total_rows']})")
    print(f"   duplicates={corrupted_quality['duplicate_paper_ids']}, stale={corrupted_quality['stale_rows_count']}")
    print(f"   is_healthy={corrupted_quality['is_healthy']} (baseline={quality['is_healthy']})")

    print("\n5. generate_phase1_report (metrics la PLACEHOLDER, chua chay evaluate that)...")
    placeholder_metrics = {
        "retrieval_hit_rate": 0.0,
        "mean_token_f1": 0.0,
        "judge_accuracy": 0.0,
        "mean_judge_score": 0.0,
        "_note": "PLACEHOLDER - chay phase1.py de co metrics that",
    }
    source_summary = {"raw_count": "N/A", "clean_count": len(df), "drop_ratio": "N/A"}
    generate_phase1_report(paths.baseline_report, source_summary, placeholder_metrics, quality, freshness)
    print(f"   Ghi -> {paths.baseline_report}")

    print("\n6. generate_corruption_report (metrics PLACEHOLDER)...")
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics=placeholder_metrics,
        corrupted_metrics=placeholder_metrics,
        repaired_metrics=placeholder_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=freshness,
    )
    print(f"   Ghi -> {paths.comparison_report}")

    print("\nRole 4 smoke test hoan tat. Tat ca ham chay khong loi.")
    print("LUU Y: metrics trong report la placeholder - phai chay phase1.py moi co so that.")


if __name__ == "__main__":
    main()
