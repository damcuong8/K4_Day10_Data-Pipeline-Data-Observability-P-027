from __future__ import annotations

from typing import Any

import pandas as pd


import json
from core.utils import first_sentence

def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build evaluation set from cleaned dataframe."""
    if len(df) < 5:
        raise ValueError(f"Not enough documents for a test set. Found {len(df)}")
    
    # Select 5 representative papers (or more if needed)
    sample_df = df.head(5)
    test_set = []
    
    for _, row in sample_df.iterrows():
        title = row['title']
        paper_id = row['paper_id']
        
        # 1. Summary Question
        summary = str(row['summary']) if pd.notnull(row['summary']) else ""
        test_set.append({
            "id": f"{paper_id}_summary",
            "question_type": "summary",
            "question": f"What is the summary of the paper '{title}'?",
            "ground_truth": first_sentence(summary) if summary else "",
            "ground_truth_doc_ids": [paper_id]
        })
        
        # 2. Authors Question
        test_set.append({
            "id": f"{paper_id}_authors",
            "question_type": "authors",
            "question": f"Who authored the paper '{title}'?",
            "ground_truth": str(row['authors_joined']),
            "ground_truth_doc_ids": [paper_id]
        })
        
        # 3. Date Question
        test_set.append({
            "id": f"{paper_id}_date",
            "question_type": "date",
            "question": f"When was the paper '{title}' published?",
            "ground_truth": str(row['published']),
            "ground_truth_doc_ids": [paper_id]
        })
        
        # 4. Categories Question
        test_set.append({
            "id": f"{paper_id}_categories",
            "question_type": "categories",
            "question": f"What categories does the paper '{title}' belong to?",
            "ground_truth": str(row['categories_joined']),
            "ground_truth_doc_ids": [paper_id]
        })

    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(test_set, f, indent=2, ensure_ascii=False)
        
    return test_set
