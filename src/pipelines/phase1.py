from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)

DEMO_QUESTION_LIMIT = 3


def _ensure_output_dirs(settings: Settings) -> None:
    """Cac ham report dung open() tran nen thu muc cha phai ton tai truoc."""
    paths = settings.paths
    for directory in (
        paths.eval_testset.parent,
        paths.quality_dir,
        paths.baseline_report.parent,
        paths.baseline_metrics.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)


# Cac cot duoc dua vao Chroma metadata; phai luon la string, khong duoc NaN.
METADATA_TEXT_COLUMNS = (
    "paper_id",
    "title",
    "published",
    "authors_joined",
    "categories_joined",
    "summary",
    "abs_url",
    "pdf_url",
    "text_for_embedding",
)


def save_clean_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    """Ghi cleaned dataframe ra CSV va JSON, bo cot datetime khong serialize duoc."""
    serializable = df.drop(columns=["published_dt"], errors="ignore")
    write_csv(serializable, csv_path)
    write_json(json_path, serializable.to_dict(orient="records"))


def load_clean_dataframe(csv_path) -> pd.DataFrame:
    """Doc cleaned CSV va khoi phuc chuoi rong.

    pd.read_csv bien o trong thanh NaN. Chroma loai bo metadata co gia tri NaN,
    khien qa.py bi KeyError khi doc metadata['categories_joined'].
    """
    df = pd.read_csv(csv_path)
    for column in METADATA_TEXT_COLUMNS:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    return df


def load_or_build_test_set(df: pd.DataFrame, settings: Settings) -> list[dict[str, Any]]:
    """Giu nguyen test set cu de baseline/corrupted/repaired so sanh cong bang."""
    testset_path = settings.paths.eval_testset
    if testset_path.exists() and not settings.refresh_test_set:
        logger.info("Reusing existing test set at %s", testset_path)
        return read_json(testset_path)
    logger.info("Building new test set at %s", testset_path)
    return build_test_set(df, testset_path)


def run_agent_demo(settings: Settings, index: LocalEmbeddingIndex, test_set: list[dict[str, Any]]) -> None:
    """Chay agent tren vai cau hoi de chung minh agent hoat dong tren corpus that."""
    demo_answers: list[dict[str, Any]] = []
    try:
        agent = build_agent(settings, index)
    except Exception as err:
        logger.warning("Skipping agent demo (%s).", err)
        write_json(settings.paths.demo_answers, {"skipped": str(err)})
        return

    for item in test_set[:DEMO_QUESTION_LIMIT]:
        question = item["question"]
        try:
            answer = run_agent_question(agent, question)
        except Exception as err:
            answer = f"Agent error: {err}"
        demo_answers.append({"question": question, "ground_truth": item["ground_truth"], "agent_answer": answer})
        print(f"  Q: {question[:90]}")
        print(f"  A: {str(answer)[:200]}\n")

    write_json(settings.paths.demo_answers, demo_answers)


def main() -> None:
    """Baseline pipeline: raw -> clean -> index -> test set -> evaluate -> quality -> report."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    paths = settings.paths
    _ensure_output_dirs(settings)

    print("=" * 70)
    print("PHASE 1 - BASELINE PIPELINE")
    print("=" * 70)

    print("\n[1/8] Fetch/load raw records tu Crossref...")
    records = fetch_source_records(settings)
    print(f"      {len(records)} raw records")

    print("\n[2/8] Clean data...")
    df = build_clean_dataframe(records, now_utc())
    if df.empty:
        raise RuntimeError("Cleaned dataframe is empty; khong the chay baseline pipeline.")
    print(f"      {len(df)} clean rows (drop {len(records) - len(df)})")

    print("\n[3/8] Save clean artifacts...")
    save_clean_dataframe(df, paths.clean_csv, paths.clean_json)
    print(f"      {paths.clean_csv}")
    print(f"      {paths.clean_json}")

    print(f"\n[4/8] Build embedding index (Chroma + {settings.embedding_provider}:{settings.embedding_model})...")
    print(f"      Embedding {len(df)} documents, co the mat 10-60s neu goi API...")
    started = time.time()
    index = LocalEmbeddingIndex.build(df=df, settings=settings, embeddings_output_path=paths.embeddings_json)
    print(f"      collection={index.collection_name}, documents={len(index.documents)} ({time.time() - started:.1f}s)")

    print("\n[5/8] Test set...")
    test_set = load_or_build_test_set(df, settings)
    print(f"      {len(test_set)} questions -> {paths.eval_testset}")

    print("\n[6/8] Evaluate baseline (goi LLM judge, hoi lau)...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"      retrieval_hit_rate = {metrics['retrieval_hit_rate']:.2%}")
    print(f"      mean_token_f1      = {metrics['mean_token_f1']:.4f}")
    print(f"      judge_accuracy     = {metrics['judge_accuracy']:.2%}")
    print(f"      mean_judge_score   = {metrics['mean_judge_score']:.2f}/5")

    print("\n[7/8] Data quality + freshness...")
    quality = run_data_quality_checks(df, settings, "baseline_quality")
    write_json(paths.quality_dir / "baseline_quality.json", quality)
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    print(f"      is_healthy={quality['is_healthy']}, duplicates={quality['duplicate_paper_ids']}, stale={quality['stale_rows_count']}")
    print(f"      is_fresh={freshness['is_fresh']}, latest={freshness['latest_published']}")

    print("\n[8/8] Markdown report + agent demo...")
    source_summary = {
        "raw_count": len(records),
        "clean_count": len(df),
        "drop_ratio": f"{(len(records) - len(df)) / len(records):.2%}" if records else "N/A",
    }
    generate_phase1_report(paths.baseline_report, source_summary, metrics, quality, freshness)
    print(f"      {paths.baseline_report}\n")
    run_agent_demo(settings, index, test_set)

    print("=" * 70)
    print("BASELINE HOAN TAT. Chay tiep: python script/run_corruption_flow.py")
    print("=" * 70)
