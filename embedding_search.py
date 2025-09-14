from config import embedding_client, search_client, AZURE_EMBED_DEPLOYMENT, AZURE_SEARCH_TEXT_FIELD, AZURE_SEARCH_EMBED_FIELD
from azure.search.documents.models import VectorizedQuery
import numpy as np
import time
from openai import RateLimitError

# Cache for embeddings to reduce API calls
embedding_cache = {}

def retrieve_relevant_docs(query, top_k=5):
    # Check cache first to avoid duplicate API calls
    if query in embedding_cache:
        print("Using cached embedding for query.")
        query_embedding = embedding_cache[query]
    else:
        # Generate embedding for the query using Azure OpenAI
        max_retries = 1
        for attempt in range(max_retries):
            try:
                response = embedding_client.embeddings.create(
                    input=[query],
                    model=AZURE_EMBED_DEPLOYMENT
                )
                query_embedding = np.array(response.data[0].embedding)
                # Cache the embedding for future use
                embedding_cache[query] = query_embedding
                print("Embedding generated and cached.")
                break
            except RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Rate limit hit on embedding, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise

    # Search in Azure AI Search
    vector_query = VectorizedQuery(vector=query_embedding, k_nearest_neighbors=top_k, fields=AZURE_SEARCH_EMBED_FIELD)
    results = search_client.search(
        search_text="",
        vector_queries=[vector_query],
        select=[AZURE_SEARCH_TEXT_FIELD]
    )

    docs = []
    for result in results:
        docs.append(result[AZURE_SEARCH_TEXT_FIELD])

    return docs
