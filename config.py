import os
from dotenv import load_dotenv
from openai import AzureOpenAI

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
import azure.cognitiveservices.speech as speechsdk

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Load environment variables
load_dotenv()

# Azure Key Vault configuration
KEY_VAULT_URL = os.getenv("AZURE_KEY_VAULT_URL")
print("Key Vault URL:", KEY_VAULT_URL)
if not KEY_VAULT_URL:
    print("Error: AZURE_KEY_VAULT_URL not found in environment variables.")
    exit(1)
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)

def get_secret(secret_name: str) -> str:
    try:
        secret = secret_client.get_secret(secret_name.replace('_', '-'))
        return secret.value
    except Exception as e:
        print(f"Error fetching secret {secret_name} from Key Vault: {e}")
        exit(1)

def get_optional_secret(secret_name: str, default: str) -> str:
    try:
        secret = secret_client.get_secret(secret_name.replace('_', '-'))
        return secret.value
    except Exception as e:
        print(f"Optional secret {secret_name} not found, using default: {default}")
        return default

# Save environment credentials to Key Vault, excluding AZURE_KEY_VAULT_URL
for key, value in os.environ.items():
    if key != "AZURE_KEY_VAULT_URL" and ("KEY" in key or "SECRET" in key or "CONNECTION_STRING" in key or "URI" in key or "API_KEY" in key):
        secret_name = key.replace('_', '-')
        try:
            # Check if secret already exists
            secret_client.get_secret(secret_name)
            print(f"Secret {key} already exists in Key Vault")
        except Exception:
            # If not exists, save it
            try:
                secret_client.set_secret(secret_name, value)
                print(f"Saved secret {key} to Key Vault")
            except Exception as e:
                print(f"Failed to save secret {key} to Key Vault: {e}")

# Azure OpenAI configuration
AZURE_OAI_ENDPOINT = get_secret("AZURE_OAI_ENDPOINT")
AZURE_OAI_KEY = get_secret("AZURE_OPENAI_API_KEY")
AZURE_OAI_DEPLOYMENT = get_secret("AZURE_CHAT_DEPLOYMENT")  # e.g., gpt-4o

# Embedding configuration
AZURE_EMBED_ENDPOINT = get_secret("AZURE_EMBED_ENDPOINT")
AZURE_EMBED_KEY = get_secret("AZURE_EMBED_KEY")
AZURE_EMBED_DEPLOYMENT = get_secret("AZURE_EMBED_DEPLOYMENT")  # e.g., text-embedding-3-large

# Azure AI Search configuration (for embedded docs)
AZURE_SEARCH_ENDPOINT = get_secret("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = get_secret("AZURE_SEARCH_KEY")

# Fetch Azure Search index name from Key Vault
AZURE_SEARCH_INDEX = get_secret("AZURE_SEARCH_INDEX")

def update_search_index():
    global AZURE_SEARCH_INDEX
    new_index = get_secret("AZURE_SEARCH_INDEX")
    if new_index != AZURE_SEARCH_INDEX:
        AZURE_SEARCH_INDEX = new_index
        # Reinitialize search_client with new index
        global search_client
        search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=AZURE_SEARCH_INDEX, credential=AzureKeyCredential(AZURE_SEARCH_KEY))
        print(f"Azure Search index updated to: {AZURE_SEARCH_INDEX}")
AZURE_SEARCH_TEXT_FIELD = get_optional_secret("AZURE_SEARCH_TEXT_FIELD", "content")  # Use your actual text field name
AZURE_SEARCH_EMBED_FIELD = get_optional_secret("AZURE_SEARCH_EMBED_FIELD", "embedding")  # Use your actual vector field name

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
AZURE_DI_ENDPOINT = get_secret("AZURE_DI_ENDPOINT")
AZURE_DI_KEY = get_secret("AZURE_DI_KEY")
di_client = DocumentIntelligenceClient(endpoint=AZURE_DI_ENDPOINT, credential=AzureKeyCredential(AZURE_DI_KEY))

# Azure Blob Storage
AZURE_BLOB_CONNECTION_STRING = get_secret("AZURE_BLOB_CONNECTION_STRING")
AZURE_BLOB_CONTAINER_NAME = get_optional_secret("AZURE_BLOB_CONTAINER_NAME", "documents")
blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)

# Azure Search Index Client
search_index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=AzureKeyCredential(AZURE_SEARCH_KEY))

# Azure Speech configuration
AZURE_SPEECH_KEY = get_secret("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = get_secret("AZURE_SPEECH_REGION")
speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)

CONF_COSMOS_URI = get_secret("COSMOS_URI")
CONF_COSMOS_KEY = get_secret("COSMOS_KEY")