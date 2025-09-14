import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from config import (
    di_client, blob_service_client, search_index_client, embedding_client,
    AZURE_BLOB_CONTAINER_NAME, AZURE_EMBED_DEPLOYMENT, AZURE_SEARCH_ENDPOINT,
    AZURE_SEARCH_KEY, AZURE_SEARCH_TEXT_FIELD, AZURE_SEARCH_EMBED_FIELD
)
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    VectorSearchVectorizer
)

def process_document_with_di(file_path):
    """Process a document with Azure Document Intelligence and return JSON result."""
    with open(file_path, "rb") as f:
        poller = di_client.begin_analyze_document(
            "prebuilt-read",  # Use prebuilt-read for general document analysis
            body=f,
            content_type="application/octet-stream"
        )
    result = poller.result()

    # Convert result to JSON
    result_json = {
        "filename": os.path.basename(file_path),
        "content": result.content,
        "pages": [
            {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "unit": page.unit,
                "lines": [
                    {
                        "content": line.content
                    } for line in page.lines
                ]
            } for page in result.pages
        ],
        "tables": [
            {
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": [
                    {
                        "row_index": cell.row_index,
                        "column_index": cell.column_index,
                        "content": cell.content
                    } for cell in table.cells
                ]
            } for table in result.tables
        ] if result.tables else []
    }

    return result_json

def upload_to_blob_storage(json_data, filename):
    """Upload JSON data to Azure Blob Storage."""
    blob_name = f"{filename}.json"
    blob_client = blob_service_client.get_blob_client(
        container=AZURE_BLOB_CONTAINER_NAME,
        blob=blob_name
    )

    json_string = json.dumps(json_data, indent=2, ensure_ascii=False)
    blob_client.upload_blob(json_string, overwrite=True)

    print(f"Uploaded {blob_name} to blob storage")
    return blob_name

def generate_embedding(text):
    """Generate embedding for text using Azure OpenAI."""
    response = embedding_client.embeddings.create(
        model=AZURE_EMBED_DEPLOYMENT,
        input=text[:8000]  # Limit text length for embedding
    )
    return response.data[0].embedding

def create_search_index(index_name):
    """Create Azure AI Search index with vector search capabilities."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name=AZURE_SEARCH_TEXT_FIELD, type=SearchFieldDataType.String),
        SearchField(
            name=AZURE_SEARCH_EMBED_FIELD,
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
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(AZURE_SEARCH_KEY)
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
                AZURE_SEARCH_TEXT_FIELD: content,
                AZURE_SEARCH_EMBED_FIELD: embedding
            }
            search_documents.append(search_doc)

    # Upload in batches
    batch_size = 100
    for i in range(0, len(search_documents), batch_size):
        batch = search_documents[i:i + batch_size]
        search_client.upload_documents(documents=batch)
        print(f"Uploaded batch {i//batch_size + 1} of {len(search_documents)//batch_size + 1}")

    print(f"Uploaded {len(search_documents)} documents to search index")

def update_env_file(index_name):
    """Update .env file with the new index name."""
    env_file = ".env"
    env_lines = []

    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            env_lines = f.readlines()

    # Update or add AZURE_SEARCH_INDEX
    index_updated = False
    for i, line in enumerate(env_lines):
        if line.startswith("AZURE_SEARCH_INDEX="):
            env_lines[i] = f"AZURE_SEARCH_INDEX={index_name}\n"
            index_updated = True
            break

    if not index_updated:
        env_lines.append(f"AZURE_SEARCH_INDEX={index_name}\n")

    with open(env_file, "w") as f:
        f.writelines(env_lines)

    print(f"Updated .env file with AZURE_SEARCH_INDEX={index_name}")

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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    index_name = f"chatbot-docs-{timestamp}"

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

    # Update environment variables
    update_env_file(index_name)

    print("Automation completed successfully!")
    print(f"New search index: {index_name}")
    print(f"Processed {len(processed_documents)} documents")

if __name__ == "__main__":
    main()
