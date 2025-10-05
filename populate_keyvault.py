from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.search import SearchManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
import time
from dotenv import load_dotenv
import os
load_dotenv()

# -----------------------------
# Config
# -----------------------------
subscription_id = os.getenv('subscription_id')
resource_group = os.getenv('resource_group')  # Note: was subscription_id, probably a typo
keyvault_url = os.getenv('keyvault_url')

# Authenticate
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=keyvault_url, credential=credential)

# -----------------------------
# Helper functions
# -----------------------------
def set_secret_force(name: str, value: str):
    """Set secret in Key Vault, automatically purging if deleted."""
    try:
        secret_client.set_secret(name, value)
        print(f"✔ Secret {name} set successfully")
    except ResourceExistsError as e:
        if "ObjectIsDeletedButRecoverable" in str(e):
            print(f"⚠ Secret {name} is deleted but recoverable. Purging...")
            secret_client.purge_deleted_secret(name)
            # wait a few seconds to let purge complete
            time.sleep(2)
            secret_client.set_secret(name, value)
            print(f"✔ Secret {name} set successfully after purge")
        else:
            raise
    except HttpResponseError as e:
        print(f"❌ Failed to set secret {name}: {e}")
        raise


# -----------------------------
# 1. Cognitive Services (Accounts + Keys + Deployments)
# -----------------------------
cog_client = CognitiveServicesManagementClient(credential, subscription_id)

# Loop through all accounts in the resource group
for account in cog_client.accounts.list_by_resource_group(resource_group):
    keys = cog_client.accounts.list_keys(resource_group, account.name)
    endpoint = account.properties.endpoint

    # Save base account info
    set_secret_force(f"{account.name}-endpoint", endpoint)
    set_secret_force(f"{account.name}-key1", keys.key1)
    set_secret_force(f"{account.name}-key2", keys.key2)

    # If this is your OpenAI account → fetch deployments
    if "oai" in account.name:  # adjust if needed
        print(f"✔ Found OpenAI account: {account.name} ({endpoint})")

        deployments = cog_client.deployments.list(resource_group, account.name)
        for dep in deployments:
            dep_name = dep.name
            dep_endpoint = f"{endpoint}openai/deployments/{dep_name}"
            set_secret_force(f"{dep_name}-deployment-endpoint", dep_endpoint)
            print(f"✔ Saved deployment endpoint for {dep_name}")

# -----------------------------
# 2. Azure Search
# -----------------------------
search_client_mgmt = SearchManagementClient(credential, subscription_id)
for search in search_client_mgmt.services.list_by_resource_group(resource_group):
    keys = search_client_mgmt.admin_keys.get(resource_group, search.name)
    endpoint = f"https://{search.name}.search.windows.net"

    set_secret_force(f"{search.name}-endpoint", endpoint)
    set_secret_force(f"{search.name}-key1", keys.primary_key)
    set_secret_force(f"{search.name}-key2", keys.secondary_key)

# -----------------------------
# 3. Storage Accounts (Blob)
# -----------------------------
storage_client = StorageManagementClient(credential, subscription_id)
for storage in storage_client.storage_accounts.list_by_resource_group(resource_group):
    keys = storage_client.storage_accounts.list_keys(resource_group, storage.name)
    conn_str = f"DefaultEndpointsProtocol=https;AccountName={storage.name};AccountKey={keys.keys[0].value};EndpointSuffix=core.windows.net"

    set_secret_force(f"{storage.name}-connection-string", conn_str)

# -----------------------------
# 4. Cosmos DB
# -----------------------------
cosmos_client = CosmosDBManagementClient(credential, subscription_id)
for cosmos in cosmos_client.database_accounts.list_by_resource_group(resource_group):
    keys = cosmos_client.database_accounts.list_keys(resource_group, cosmos.name)
    set_secret_force(f"{cosmos.name}-primary-key", keys.primary_master_key)
    set_secret_force(f"{cosmos.name}-secondary-key", keys.secondary_master_key)
    set_secret_force(f"{cosmos.name}-uri", cosmos.document_endpoint)

print("✔ All Azure resources discovered and secrets saved to Key Vault")
