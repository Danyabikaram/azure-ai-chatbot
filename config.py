import os
from dotenv import load_dotenv
from openai import AzureOpenAI

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
import azure.cognitiveservices.speech as speechsdk

# Load environment variables
load_dotenv()

# Azure OpenAI configuration
AZURE_OAI_ENDPOINT = os.getenv("AZURE_OAI_ENDPOINT")
AZURE_OAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OAI_DEPLOYMENT = os.getenv("AZURE_CHAT_DEPLOYMENT")  # e.g., gpt-4o

# Embedding configuration
AZURE_EMBED_ENDPOINT = os.getenv("AZURE_EMBED_ENDPOINT")
AZURE_EMBED_KEY = os.getenv("AZURE_EMBED_KEY")
AZURE_EMBED_DEPLOYMENT = os.getenv("AZURE_EMBED_DEPLOYMENT")  # e.g., text-embedding-3-large

# Azure AI Search configuration (for embedded docs)
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
AZURE_SEARCH_TEXT_FIELD = os.getenv("AZURE_SEARCH_TEXT_FIELD", "content")  # Use your actual text field name
AZURE_SEARCH_EMBED_FIELD = os.getenv("AZURE_SEARCH_EMBED_FIELD", "embedding")  # Use your actual vector field name

# Initialize Azure clients
try:
    chat_client = AzureOpenAI(
        base_url=AZURE_OAI_ENDPOINT,
        api_key=AZURE_OAI_KEY,
        api_version="2024-12-01-preview"
    )

    embedding_client = AzureOpenAI(
        base_url=AZURE_EMBED_ENDPOINT,
        api_key=AZURE_EMBED_KEY,
        api_version="2023-05-15"
    )
except Exception as e:
    print("Error initializing Azure OpenAI clients:", e)
    exit(1)

# Azure AI Search client
search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=AZURE_SEARCH_INDEX, credential=AzureKeyCredential(AZURE_SEARCH_KEY))

# Azure Document Intelligence
AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT")
AZURE_DI_KEY = os.getenv("AZURE_DI_KEY")
di_client = DocumentIntelligenceClient(endpoint=AZURE_DI_ENDPOINT, credential=AzureKeyCredential(AZURE_DI_KEY))

# Azure Blob Storage
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME", "documents")
blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)

# Azure Search Index Client
search_index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=AzureKeyCredential(AZURE_SEARCH_KEY))

# Azure Speech configuration
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
