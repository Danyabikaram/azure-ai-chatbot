from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
import os

load_dotenv()

# -----------------------------
# Config
# -----------------------------
keyvault_url = os.getenv('keyvault_url')

# Authenticate
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=keyvault_url, credential=credential)


def get_secret(name: str) -> str:
    """Retrieve secret from Key Vault."""
    try:
        return secret_client.get_secret(name).value
    except Exception as e:
        print(f" Failed to retrieve secret {name}: {e}")
        raise


def get_region_from_endpoint(endpoint: str) -> str:
    """Extract region from endpoint like https://<name>.<region>.cognitiveservices.azure.com/"""
    try:
        return endpoint.split(".")[1]
    except Exception:
        return "eastus2"


# -----------------------------
# Initialize Azure Clients using Key Vault secrets
# -----------------------------

try:
    # OpenAI Chat + Embeddings
    OAI_ENDPOINT = get_secret("oai-internship-eus2-endpoint")
    CHAT_OAI_CLIENT = get_secret("gpt-4o-deployment-endpoint") + "/chat/completions?api-version=2025-01-01-preview"
    EMBEDDED_OAI_CLIENT = get_secret("text-embedding-3-large-deployment-endpoint") + "/embeddings?api-version=2023-05-15"
    print("CHAT_OAI_CLIENT : ", CHAT_OAI_CLIENT)
    print("EMBEDDED_OAI_CLIENT : ", EMBEDDED_OAI_CLIENT)
    OAI_KEY = get_secret("oai-internship-eus2-key1")

    chat_client = AzureOpenAI(base_url=CHAT_OAI_CLIENT, api_key=OAI_KEY, api_version="2024-12-01-preview")
    embedding_client = AzureOpenAI(base_url=EMBEDDED_OAI_CLIENT, api_key=OAI_KEY, api_version="2023-05-15")

    # Document Intelligence
    DI_ENDPOINT = get_secret("text-embedding-3-large-deployment-endpoint")
    DI_KEY = get_secret("di-internship-eus2-key1")
    di_client = DocumentIntelligenceClient(endpoint=DI_ENDPOINT, credential=AzureKeyCredential(DI_KEY))

    # Blob Storage
    BLOB_CONN = get_secret("sainternshipeus-connection-string")
    blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONN)

    # Speech
    SPEECH_ENDPOINT = get_secret("sps-internship-eus2-endpoint")
    SPEECH_KEY = get_secret("sps-internship-eus2-key1")
    SPEECH_REGION = get_region_from_endpoint(SPEECH_ENDPOINT)
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)

    # Search
    SEARCH_ENDPOINT = get_secret("ss-internship-eus2-endpoint")
    SEARCH_KEY = get_secret("ss-internship-eus2-key1")
    SEARCH_INDEX = "chatbot-docs-20250913_145142"
    search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX, credential=AzureKeyCredential(SEARCH_KEY))
    search_index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=AzureKeyCredential(SEARCH_KEY))

    # Cosmos DB
    COSMOS_URI = get_secret("cosmosdb-internship-wus2-uri")
    COSMOS_KEY = get_secret("cosmosdb-internship-wus2-primary-key")

    # Realtime API
    REALTIME_ENDPOINT = get_secret("gpt-realtime-endpoint")
    REALTIME_KEY = get_secret("oai-internship-eus2-key1")

    print("All Azure clients initialized successfully using Key Vault secrets")

except Exception as e:
    print(f" Failed to initialize clients: {e}")
    raise


# -----------------------------
# Realtime helpers
# -----------------------------
def build_realtime_ws_url(endpoint: str | None = None,
                          api_key: str | None = None,
                          deployment: str | None = None,
                          api_version: str | None = None) -> str:
    """Build a browser-usable WebSocket URL for Azure OpenAI Realtime.

    Notes:
    - Browsers cannot set custom headers on WebSocket handshake, so we include
      the api-key as a query parameter. This URL should only be issued from a trusted backend.
    - If the provided endpoint already points to the realtime path, we preserve it.
    - Otherwise we append "/openai/realtime" and add deployment/api-version when provided.
    """
    endpoint = (endpoint or REALTIME_ENDPOINT or "").strip()
    api_key = api_key or REALTIME_KEY
    if not endpoint:
        raise ValueError("Realtime endpoint is not configured")
    if not api_key:
        raise ValueError("Realtime API key is not configured")

    parsed = urlparse(endpoint)
    scheme = 'wss' if parsed.scheme in ('http', 'https') else (parsed.scheme or 'wss')

    path = parsed.path or ''
    if 'openai/realtime' not in path:
        base_path = path.rstrip('/')
        path = f"{base_path}/openai/realtime"

    query_params = dict(parse_qsl(parsed.query))
    if deployment:
        query_params['deployment'] = deployment
    if api_version:
        query_params['api-version'] = api_version
    query_params['api-key'] = api_key

    new_query = urlencode(query_params)
    ws_url = urlunparse((scheme, parsed.netloc, path, '', new_query, ''))
    return ws_url


def GetRealTimeClient(api_key: str | None = None,
                      endpoint: str | None = None,
                      deployment_name: str | None = None,
                      api_version: str | None = None):
    """Return a dict with a ready-to-use WS URL and metadata.

    This mirrors server-side connection creation but returns a browser-usable
    WS URL so the client can connect directly without exposing keys in code.
    """
    ws_url = build_realtime_ws_url(
        endpoint=endpoint or REALTIME_ENDPOINT,
        api_key=api_key or REALTIME_KEY,
        deployment=deployment_name,
        api_version=api_version
    )
    return {"ws_url": ws_url}

