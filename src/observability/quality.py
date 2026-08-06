from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import pandas as pd

from core.config import Settings

# Cot text can theo doi ti le rong; rong 100% nghia la nguon khong tra ve truong nay.
MONITORED_TEXT_COLUMNS = ("title", "summary", "authors_joined", "categories_joined")


def _empty_ratio(series: pd.Series) -> float:
    """Ti le o rong: tinh ca NaN lan chuoi rong sau khi strip."""
    normalized = series.fillna("").astype(str).str.strip()
    return float((normalized == "").mean())


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run observability signals and record quality metrics."""
    total_rows = len(df)

    # Check nulls in critical columns
    critical_cols = ['paper_id', 'title', 'summary', 'published']
    null_counts = df[critical_cols].isnull().sum().to_dict() if not df.empty else {}

    # Check duplicates
    duplicate_count = df['paper_id'].duplicated().sum() if not df.empty else 0

    # Check freshness
    max_age_days = df['age_days'].max() if not df.empty else 0
    stale_rows_count = (df['age_days'] > settings.freshness_threshold_days).sum() if not df.empty else 0

    # Check completeness: cot nao rong hoan toan thi khong dung de danh gia duoc
    empty_ratios = {
        column: round(_empty_ratio(df[column]), 4)
        for column in MONITORED_TEXT_COLUMNS
        if column in df.columns
    }
    fully_empty_columns = [column for column, ratio in empty_ratios.items() if ratio >= 1.0]

    quality_report = {
        "report_name": report_name,
        "total_rows": int(total_rows),
        "null_counts": {k: int(v) for k, v in null_counts.items()},
        "duplicate_paper_ids": int(duplicate_count),
        "max_age_days": float(max_age_days),
        "stale_rows_count": int(stale_rows_count),
        "stale_ratio": float(stale_rows_count / total_rows) if total_rows > 0 else 0.0,
        "empty_ratios": empty_ratios,
        "fully_empty_columns": fully_empty_columns,
        "is_healthy": bool(
            duplicate_count == 0
            and stale_rows_count == 0
            and sum(null_counts.values()) == 0
            and not fully_empty_columns
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Tu ghi artifact vao data/quality/ thay vi de pipeline phai nho lam ho.
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.paths.quality_dir / f"{report_name}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(quality_report, f, indent=2, ensure_ascii=False)

    return quality_report

def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and save freshness report."""
    if df.empty:
        report = {"error": "Empty dataframe"}
    else:
        # Convert published strings to datetime objects for comparison
        dates = pd.to_datetime(df['published'], errors='coerce')
        latest_published = dates.max().strftime('%Y-%m-%d') if not dates.isnull().all() else None
        oldest_published = dates.min().strftime('%Y-%m-%d') if not dates.isnull().all() else None
        
        stale_rows = int((df['age_days'] > settings.freshness_threshold_days).sum())
        total_rows = len(df)
        
        report = {
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "is_fresh": bool(stale_rows == 0),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    return report
