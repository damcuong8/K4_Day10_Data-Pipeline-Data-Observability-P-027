from __future__ import annotations

import pandas as pd


import json
import logging
import random
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    """Helper to rebuild text_for_embedding with the same format as cleaning.py."""
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate data corruption and save a log of changes."""
    logger.info("Starting corruption process on %d records.", len(df))
    if df.empty:
        return df

    corrupted_df = df.copy()
    logs: list[dict[str, Any]] = []

    def add_log(action: str, paper_id: str, before: Any, after: Any):
        logs.append({
            "action": action,
            "paper_id": paper_id,
            "before": before,
            "after": after,
        })

    # Set random seed for reproducibility in testing
    random.seed(42)

    total = len(corrupted_df)

    # 1. Drop latest records (lowest age_days) - 10%
    drop_count = max(1, int(total * 0.1))
    latest_indices = corrupted_df.nsmallest(drop_count, 'age_days').index
    for idx in latest_indices:
        add_log("DROP_LATEST", corrupted_df.loc[idx, 'paper_id'], "Exists", "Dropped")
    corrupted_df = corrupted_df.drop(latest_indices)
    logger.info("Dropped %d latest records.", len(latest_indices))

    if corrupted_df.empty:
        return corrupted_df

    # Reset index to easily sample remaining rows
    corrupted_df = corrupted_df.reset_index(drop=True)

    # Calculate sub-counts
    remaining = len(corrupted_df)
    blank_summary_count = max(1, int(remaining * 0.1))
    noise_count = max(1, int(remaining * 0.05))
    truncate_count = max(1, int(remaining * 0.05))
    stale_count = max(1, int(remaining * 0.05))

    # Shuffle indices to apply different corruptions
    indices = list(corrupted_df.index)
    random.shuffle(indices)

    # 2. Blank summary
    blank_idx = indices[:blank_summary_count]
    indices = indices[blank_summary_count:]
    for idx in blank_idx:
        before = corrupted_df.loc[idx, 'summary']
        after = ""
        corrupted_df.loc[idx, 'summary'] = after
        add_log("BLANK_SUMMARY", corrupted_df.loc[idx, 'paper_id'], before, after)
    logger.info("Blanked summary for %d records.", len(blank_idx))

    # 3. Inject noise into title
    noise_idx = indices[:noise_count]
    indices = indices[noise_count:]
    for idx in noise_idx:
        before = corrupted_df.loc[idx, 'title']
        after = f"{before} [IRRELEVANT NOISE DATA CORRUPTION]"
        corrupted_df.loc[idx, 'title'] = after
        add_log("INJECT_NOISE", corrupted_df.loc[idx, 'paper_id'], before, after)
    logger.info("Injected noise into %d records.", len(noise_idx))

    # 4. Truncate title
    truncate_idx = indices[:truncate_count]
    indices = indices[truncate_count:]
    for idx in truncate_idx:
        before = corrupted_df.loc[idx, 'title']
        after = before[:10] if isinstance(before, str) else before
        corrupted_df.loc[idx, 'title'] = after
        add_log("TRUNCATE_TITLE", corrupted_df.loc[idx, 'paper_id'], before, after)
    logger.info("Truncated title for %d records.", len(truncate_idx))

    # 5. Make published date stale (add 1000 to age_days)
    stale_idx = indices[:stale_count]
    indices = indices[stale_count:]
    for idx in stale_idx:
        before = int(corrupted_df.loc[idx, 'age_days'])
        after = before + 1000
        corrupted_df.loc[idx, 'age_days'] = after
        add_log("STALE_DATE", corrupted_df.loc[idx, 'paper_id'], before, after)
    logger.info("Made %d records stale.", len(stale_idx))

    # 6. Add duplicate rows (take up to 3 random rows and append them)
    dup_candidates = corrupted_df.sample(n=min(3, len(corrupted_df)))
    for _, row in dup_candidates.iterrows():
        add_log("DUPLICATE_ROW", row['paper_id'], "Single", "Duplicated")
    
    corrupted_df = pd.concat([corrupted_df, dup_candidates], ignore_index=True)
    logger.info("Added %d duplicate records.", len(dup_candidates))

    # 7. Rebuild text_for_embedding for ALL rows since many were modified
    corrupted_df["text_for_embedding"] = corrupted_df.apply(_rebuild_text_for_embedding, axis=1)

    # 8. Save corruption log
    log_path = Path(output_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    logger.info("Saved corruption log to %s", log_path)

    return corrupted_df
