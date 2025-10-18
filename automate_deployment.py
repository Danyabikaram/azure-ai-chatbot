import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from config import (
    search_index_client, embedding_client,
    SEARCH_ENDPOINT,
    SEARCH_KEY
)
from document_loader import process_document_with_di , upload_to_blob_storage 
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)


##embeddings for the doc
def generate_embedding(text):
    """Generate embedding for text using Azure OpenAI."""
    response = embedding_client.embeddings.create(
        model='text-embedding-3-large',
        input=text[:8000]  # Limit text length for embedding
    )
    return response.data[0].embedding

def create_search_index(index_name):
    """Create Azure AI Search index with vector search capabilities."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name='content', type=SearchFieldDataType.String),
        SearchField(
            name='embedding',
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=3072,  # Dimension for text-embedding-3-large
            vector_search_profile_name="my-vector-profile"
        )
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="my-hnsw")
        ],
        profiles=[
            VectorSearchProfile(
                name="my-vector-profile",
                algorithm_configuration_name="my-hnsw"
            )
        ]
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search
    )

    search_index_client.create_index(index)
    print(f"Created search index with vector search: {index_name}")
    return index_name

def upload_documents_to_search(documents, index_name):
    """Upload documents to Azure AI Search index."""
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    import numpy as np

    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(SEARCH_KEY)
    )

    # Prepare documents for upload
    search_documents = []
    for doc in documents:
        content = doc.get('content', '')
        if content:
            embedding = generate_embedding(content)
            # Ensure embedding is a list of floats
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            search_doc = {
                "id": str(uuid.uuid4()),
                'content': content,
                'embedding': embedding
            }
            search_documents.append(search_doc)

    # Upload in batches
    batch_size = 100
    for i in range(0, len(search_documents), batch_size):
        batch = search_documents[i:i + batch_size]
        search_client.upload_documents(documents=batch)
        print(f"Uploaded batch {i//batch_size + 1} of {len(search_documents)//batch_size + 1}")

    print(f"Uploaded {len(search_documents)} documents to search index")



def main():
    """Main automation function."""
    rag_folder = Path("rag")
    if not rag_folder.exists():
        print("rag folder not found!")
        return

    # Get all files in rag folder
    files = list(rag_folder.glob("*"))
    if not files:
        print("No files found in rag folder!")
        return

    print(f"Found {len(files)} files to process")

    # Process each file
    processed_documents = []
    for file_path in files:
        if file_path.is_file():
            print(f"Processing {file_path.name}...")
            try:
                # Process with Document Intelligence
                json_result = process_document_with_di(file_path)

                # Upload to Blob Storage
                blob_name = upload_to_blob_storage(json_result, file_path.stem)

                # Store for search upload
                processed_documents.append(json_result)

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                continue

    if not processed_documents:
        print("No documents were successfully processed!")
        return

    # Create new search index
    index_name = "chatbot-docs-20250913_145142"

    try:
        create_search_index(index_name)
    except Exception as e:
        print(f"Error creating search index: {e}")
        return

    # Upload documents to search index
    try:
        upload_documents_to_search(processed_documents, index_name)
    except Exception as e:
        print(f"Error uploading documents to search: {e}")
        return


    print("Automation completed successfully!")
    print(f"New search index: {index_name}")
    print(f"Processed {len(processed_documents)} documents")

if __name__ == "__main__":
    main()
