import pandas as pd
from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent, run_agent_question
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    settings = load_settings()
    
    logger.info("Loading clean data from %s", settings.paths.clean_json)
    df = pd.read_json(settings.paths.clean_json, encoding="utf-8")
    
    logger.info("Building MiniLM embeddings and Chroma collection (papers-baseline)...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json
    )
    logger.info("Successfully built collection: %s with %d documents.", index.collection_name, len(index.documents))
    
    # Test semantic search
    query = "agentic retrieval augmented generation"
    logger.info("Testing semantic search with query: '%s'", query)
    results = index.search(query, top_k=2)
    for r in results:
        logger.info("Found: %s (Score: %.4f)", r.title, r.score)
        
    # Test exact lookup
    lookup_title = results[0].title if results else "No Title"
    logger.info("Testing exact lookup for title: '%s'", lookup_title)
    record = index.lookup(lookup_title)
    if record:
        logger.info("Exact lookup successful! Found paper_id: %s", record['paper_id'])
    
    # Test Agent
    logger.info("Building Agent...")
    agent = build_agent(settings, index)
    
    agent_query = f"Can you summarize the paper titled '{lookup_title}'?"
    logger.info("Testing Agent with query: '%s'", agent_query)
    answer = run_agent_question(agent, agent_query)
    logger.info("Agent Answer:\n%s", answer)
    
    logger.info("CP2 Role 3 execution completed successfully.")

if __name__ == "__main__":
    main()
