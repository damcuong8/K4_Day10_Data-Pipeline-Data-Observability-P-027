import pandas as pd
from pathlib import Path
from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent, run_agent_question

def main():
    settings = load_settings()
    
    # Fake data to test embedding and agent indexing
    dummy_data = [
        {
            "paper_id": "10.1234/test.1",
            "title": "Agentic RAG using LLMs",
            "text_for_embedding": "Agentic RAG using LLMs. This paper explores how large language models can use tools to retrieve information dynamically.",
            "published": "2026-08-01",
            "authors_joined": "John Doe, Jane Smith",
            "categories_joined": "Computer Science, AI",
            "summary": "This paper explores how large language models can use tools to retrieve information dynamically.",
            "abs_url": "http://example.com/abs",
            "pdf_url": "http://example.com/pdf"
        },
        {
            "paper_id": "10.1234/test.2",
            "title": "Data Observability in Pipelines",
            "text_for_embedding": "Data Observability in Pipelines. A study on how data corruption affects downstream systems.",
            "published": "2026-08-05",
            "authors_joined": "Alice Bob",
            "categories_joined": "Data Science",
            "summary": "A study on how data corruption affects downstream systems.",
            "abs_url": "http://example.com/abs2",
            "pdf_url": "http://example.com/pdf2"
        }
    ]
    
    df = pd.DataFrame(dummy_data)
    
    print("1. Building test index...")
    # Using a dummy path for this test so we don't mess up the actual pipeline
    test_json_path = settings.paths.chroma_dir / "test_embeddings.json"
    
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=test_json_path
    )
    print(f"Index built successfully: {index.collection_name}")
    print(f"Total documents: {len(index.documents)}")
    
    print("\n2. Testing Semantic Search...")
    search_results = index.search("agentic retrieval", top_k=1)
    if search_results:
        print(f"Found: {search_results[0].title} with score {search_results[0].score:.4f}")
    
    print("\n3. Testing Agent...")
    agent = build_agent(settings, index)
    
    # We will test a simple question
    q = "Who authored the paper 'Agentic RAG using LLMs'?"
    print(f"Question: {q}")
    ans = run_agent_question(agent, q)
    print(f"Answer: {ans}")
    
    print("\nSmoke test for Role 3 components completed successfully.")

if __name__ == "__main__":
    main()
