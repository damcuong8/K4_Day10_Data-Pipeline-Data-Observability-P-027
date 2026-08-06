import pandas as pd
from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from ingestion.corruption import corrupt_clean_dataframe
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    settings = load_settings()
    
    # --- CP5: Corruption Flow ---
    logger.info("=== CP5: Building Corrupted Dataset and Index ===")
    logger.info("Loading baseline clean data...")
    clean_df = pd.read_json(settings.paths.clean_json, encoding="utf-8")
    
    logger.info("Running Role 2 corruption logic...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=False)
    
    logger.info("Building papers-corrupted index...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    logger.info("papers-corrupted built successfully.")
    
    query = "agentic retrieval augmented generation"
    logger.info("Testing search on corrupted index...")
    res_corrupt = corrupted_index.search(query, top_k=2)
    for r in res_corrupt:
        logger.info("Corrupted Found: %s (Score: %.4f)", r.title, r.score)

    logger.info("Checking baseline index is still isolated...")
    baseline_index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    res_baseline = baseline_index.search(query, top_k=2)
    logger.info("Baseline Top 1: %s", res_baseline[0].title if res_baseline else "None")


    # --- CP6: Repair Flow ---
    logger.info("=== CP6: Building Repaired Dataset and Index ===")
    logger.info("Simulating Repair by restoring from clean baseline...")
    clean_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=False)
    
    logger.info("Building papers-repaired index...")
    repaired_index = LocalEmbeddingIndex.build(
        df=clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    logger.info("papers-repaired built successfully.")
    
    logger.info("Testing search on repaired index...")
    res_repair = repaired_index.search(query, top_k=2)
    for r in res_repair:
        logger.info("Repaired Found: %s (Score: %.4f)", r.title, r.score)

    logger.info("CP5 and CP6 execution completed successfully!")

if __name__ == "__main__":
    main()
