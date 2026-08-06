from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord

logger = logging.getLogger(__name__)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a dataframe ready for embedding.

    1. Parse PaperRecord list into Pandas DataFrame.
    2. Drop records with missing mandatory fields.
    3. Deduplicate based on paper_id.
    4. Calculate age_days and filter out future dates.
    5. Construct helper columns: authors_joined, categories_joined.
    6. Construct text_for_embedding.
    """
    logger.info("Starting data cleaning with %d records.", len(records))
    
    if not records:
        return pd.DataFrame()

    # Convert records to list of dicts, then to DataFrame
    df = pd.DataFrame([vars(r) for r in records])

    # 1. Drop missing mandatory fields
    # Ensure they are not empty strings or None
    df = df.replace(r"^\s*$", None, regex=True)
    df = df.dropna(subset=["paper_id", "title", "summary", "published"])

    # 2. Drop duplicates on paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # 3. Handle Dates and age_days
    # Convert 'published' to datetime
    df["published_dt"] = pd.to_datetime(df["published"], errors="coerce")
    df = df.dropna(subset=["published_dt"])
    
    # Calculate age_days
    # run_date is datetime, we take .date() or normalize
    run_date_norm = pd.to_datetime(run_date.date())
    df["age_days"] = (run_date_norm - df["published_dt"]).dt.days
    
    # Filter negative age_days (future dates)
    df = df[df["age_days"] >= 0].copy()

    # 4. Helper Columns
    df["authors_joined"] = df["authors"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df["categories_joined"] = df["categories"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df["summary_chars"] = df["summary"].apply(lambda x: len(str(x)))

    # 5. text_for_embedding
    def create_text_for_embedding(row: pd.Series) -> str:
        return (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        )

    df["text_for_embedding"] = df.apply(create_text_for_embedding, axis=1)

    # 6. Final cleanup (sort, drop temp columns if desired)
    df = df.sort_values("published_dt", ascending=False).reset_index(drop=True)
    
    logger.info("Cleaning completed. %d records remaining.", len(df))
    return df
