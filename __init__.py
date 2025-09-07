import os
import uuid
from dotenv import load_dotenv
import tiktoken
import numpy as np
from openai import AzureOpenAI, APIConnectionError, RateLimitError, APIStatusError
from azure.cosmos import CosmosClient
from azure.cosmos.partition_key import PartitionKey
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
import azure.functions as func
import logging
import json
# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()

# Azure OpenAI configuration
AZURE_OAI_ENDPOINT = os.getenv("AZURE_OAI_ENDPOINT")
AZURE_OAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OAI_DEPLOYMENT = os.getenv("AZURE_CHAT_DEPLOYMENT")  # e.g., gpt-4o

# Embedding configuration
AZURE_EMBED_ENDPOINT = os.getenv("AZURE_EMBED_ENDPOINT")
AZURE_EMBED_KEY = os.getenv("AZURE_EMBED_KEY")
AZURE_EMBED_DEPLOYMENT = os.getenv("AZURE_EMBED_DEPLOYMENT")  # e.g., text-embedding-3-large

# Cosmos DB configuration (for sessions)
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = "ChatbotDB"
CONTAINER_NAME = "Sessions"

# Azure AI Search configuration (for embedded docs)
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
AZURE_SEARCH_TEXT_FIELD = os.getenv("AZURE_SEARCH_TEXT_FIELD", "content")  # Use your actual text field name
AZURE_SEARCH_EMBED_FIELD = os.getenv("AZURE_SEARCH_EMBED_FIELD", "embedding")  # Use your actual vector field name

# ---------------------------
# Initialize Azure clients
# ---------------------------
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

# Cosmos DB client
cosmos_client = CosmosClient(COSMOS_URI, COSMOS_KEY)
database = cosmos_client.create_database_if_not_exists(DATABASE_NAME)
container = database.create_container_if_not_exists(
    id=CONTAINER_NAME,
    partition_key=PartitionKey(path="/sessionId")
)

# Azure AI Search client
search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=AZURE_SEARCH_INDEX, credential=AzureKeyCredential(AZURE_SEARCH_KEY))

# ---------------------------
# Session Management
# ---------------------------
session_id = str(uuid.uuid4())
print(f"Your SessionID: {session_id}")

def restart_session():
    global session_id
    session_id = str(uuid.uuid4())
    print(f"\nNew Session started. Your SessionID: {session_id}\n")
    return session_id

def save_message(session_id, role, content):
    container.create_item({
        "id": str(uuid.uuid4()),
        "sessionId": session_id,
        "role": role,
        "content": content
    })

def load_messages(session_id):
    query = f"SELECT c.role, c.content FROM c WHERE c.sessionId = '{session_id}' ORDER BY c._ts ASC"
    items = list(container.query_items(query, enable_cross_partition_query=True))
    return [{"role": i["role"], "content": i["content"]} for i in items]

def clear_conversation(session_id):
    query = f"SELECT c.id, c.sessionId FROM c WHERE c.sessionId = '{session_id}'"
    items = list(container.query_items(query, enable_cross_partition_query=True))
    for item in items:
        container.delete_item(item["id"], partition_key=item["sessionId"])

# ---------------------------
# Token & Summarization
# ---------------------------
encoding = tiktoken.encoding_for_model("gpt-4o")
MAX_TOKENS = 4000
RESERVED_TOKENS = 500
SUMMARIZE_AFTER = 25

def num_tokens_from_messages(messages):
    return sum(len(encoding.encode(m["content"])) for m in messages)

def trim_history(history):
    while num_tokens_from_messages(history) > (MAX_TOKENS - RESERVED_TOKENS):
        if len(history) > 2:
            history.pop(1)
        else:
            break
    return history

def summarize_conversation(history):
    summary_prompt = [
        {"role": "system", "content": "Summarize the following conversation in less than 100 words."},
        {"role": "user", "content": str(history)}
    ]
    summary = chat_client.chat.completions.create(
        model=AZURE_OAI_DEPLOYMENT,
        messages=summary_prompt,
        max_tokens=150
    )
    return summary.choices[0].message.content

# ---------------------------
# Embedding & Similarity Search
# ---------------------------
def retrieve_relevant_docs(user_input, k=3):
    print(f"Retrieving docs for query: '{user_input}'")

    # Generate embedding
    query_embedding = embedding_client.embeddings.create(
        model=AZURE_EMBED_DEPLOYMENT,
        input=user_input
    ).data[0].embedding
    print(f"Query embedding generated, length: {len(query_embedding)}")

    # Perform vector search
    results = search_client.search(
        search_text="",
        vector_queries=[VectorizedQuery(vector=query_embedding, k_nearest_neighbors=k, fields=AZURE_SEARCH_EMBED_FIELD)],
        select=[AZURE_SEARCH_TEXT_FIELD]
    )

    docs = list(results)
    print(f"Found {len(docs)} documents in search index")

    if not docs:
        return "No documents available for retrieval."

    # Safely join text fields
    top_docs = docs[:k]
    result = "\n\n".join([str(doc.get(AZURE_SEARCH_TEXT_FIELD) or "") for doc in top_docs])
    print(f"Returning {len(result)} characters of context")
    return result

# ---------------------------
# Generate RAG response
# ---------------------------
def generate_rag_response(user_query, history):
    top_docs_text = retrieve_relevant_docs(user_query, k=3)

    messages = [
        {"role": "system", "content": (
            "You are an AI assistant. ONLY answer questions using the retrieved documents. "
            "If the answer is not in the documents, respond with 'I don't know.'"
        )},
        {"role": "user", "content": user_query + "\n\nContext:\n" + top_docs_text}
    ] + history[-10:]

    response = chat_client.chat.completions.create(
        model=AZURE_OAI_DEPLOYMENT,
        messages=messages,
        max_tokens=500,
        temperature=0.2,
        top_p=0.9,
        presence_penalty=0.6,
        frequency_penalty=0.5
    )

    return response.choices[0].message.content

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Chat request received.")
    global session_id

    try:
       
        try:
            req_body = req.get_json()
        except Exception as e:
            logging.error(f"Invalid JSON: {e}")
            return func.HttpResponse(
                json.dumps({"reply": "Invalid JSON."}),
                status_code=400
            )

        user_text = req_body.get("message", "")
        if not user_text:
            return func.HttpResponse(
                json.dumps({"reply": "No message provided."}),
                status_code=400
            )

        user_text = user_text.strip().lower()
        logging.info(f"User input: {user_text}")
        logging.info(f"Current session_id: {session_id}")

        # --- Handle chatbot commands ---
        if user_text == "restart":
            session_id = str(uuid.uuid4())
            logging.info(f"Session restarted: {session_id}")
            return func.HttpResponse(
                json.dumps({"reply": f"Session restarted! New SessionID: {session_id}"}),
                status_code=200
            )

        elif user_text == "clear":
            clear_conversation(session_id)
            logging.info("Conversation cleared")
            return func.HttpResponse(
                json.dumps({"reply": "Conversation cleared!"}),
                status_code=200
            )

        elif user_text == "show history":
            history = load_messages(session_id)
            if not history:
                return func.HttpResponse(
                    json.dumps({"reply": "No messages found for this session."}),
                    status_code=200
                )
            history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])
            return func.HttpResponse(
                json.dumps({"reply": history_text}),
                status_code=200
            )

        # --- Normal chat flow ---
        save_message(session_id, "user", user_text)
        history = load_messages(session_id)

        # Generate response using RAG
        reply = generate_rag_response(user_text, history)
        logging.info(f"Assistant reply: {reply}")

        save_message(session_id, "assistant", reply)

        return func.HttpResponse(
            json.dumps({"reply": reply}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Unhandled error: {e}")
        return func.HttpResponse(
            json.dumps({"reply": "Server error."}),
            status_code=500,
            mimetype="application/json"
        )
