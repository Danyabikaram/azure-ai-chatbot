import os
import json
from config import di_client, blob_service_client, AZURE_BLOB_CONTAINER_NAME

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

def load_rag_documents(rag_folder="rag"):
    documents = []
    for file in os.listdir(rag_folder):
        if file.endswith((".pdf", ".png", ".jpg", ".jpeg", ".tiff")):  # Support more formats
            file_path = os.path.join(rag_folder, file)
            try:
                # Process with Document Intelligence
                json_result = process_document_with_di(file_path)

                # Upload JSON to Blob Storage
                upload_to_blob_storage(json_result, os.path.splitext(file)[0])

                # Store for potential further processing
                documents.append(json_result)
            except Exception as e:
                print(f"Error processing {file}: {e}")
    return documents
