import os
import uuid
from dotenv import load_dotenv
import tiktoken
from openai import AzureOpenAI, APIConnectionError, RateLimitError, APIStatusError
from azure.cosmos import CosmosClient
from azure.cosmos.partition_key import PartitionKey
import azure.functions as func
import logging

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()

# Azure OpenAI configuration
AZURE_OAI_ENDPOINT = os.getenv("AZURE_OAI_ENDPOINT")
AZURE_OAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OAI_DEPLOYMENT = os.getenv("AZURE_CHAT_DEPLOYMENT")  # e.g., gpt-4o

# Azure Search (for RAG extensions)
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

# Cosmos DB configuration
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = "ChatbotDB"
CONTAINER_NAME = "Sessions"

# ---------------------------
# Initialize Azure clients
# ---------------------------
try:
    chat_client = AzureOpenAI(
        base_url=AZURE_OAI_ENDPOINT,
        api_key=AZURE_OAI_KEY,
        api_version="2024-12-01-preview"
    )
except Exception as e:
    print("Error initializing Azure OpenAI client:", e)
    exit(1)

# Cosmos DB client
cosmos_client = CosmosClient(COSMOS_URI, COSMOS_KEY)
database = cosmos_client.create_database_if_not_exists(DATABASE_NAME)
container = database.create_container_if_not_exists(
    id=CONTAINER_NAME,
    partition_key=PartitionKey(path="/sessionId")
)

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
            history.pop(1)  # remove earliest non-system message
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
# RAG using Azure OpenAI extensions
# ---------------------------
extension_config = [
    {
        "type": "azure_search",
        "parameters": {
            "endpoint": AZURE_SEARCH_ENDPOINT,
            "index_name": AZURE_SEARCH_INDEX,
            "authentication": {"type": "api_key", "key": AZURE_SEARCH_KEY},
            "in_scope": True,
        },
    }
]

def generate_rag_response(user_query, history):
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant. ONLY answer questions using information retrieved from documents via RAG. "
                "Do NOT use your own knowledge. If the answer is not in the documents, respond with 'I don't know.' "
                "Include references or links whenever possible. Provide clear step-by-step explanations and examples. "
                "After the answer, suggest related topics or next steps, and ask if the user wants further help."
            )
        },
        {"role": "user", "content": user_query}
    ] + history[-10:]

    response = chat_client.chat.completions.create(
        model=AZURE_OAI_DEPLOYMENT,
        messages=messages,
        max_tokens=500,
        temperature=0.2,
        top_p=0.9,
        presence_penalty=0.6,
        frequency_penalty=0.5,
        extra_body={"data_sources": extension_config}  # ✅ pass your RAG source here
    )

    return response.choices[0].message.content

# ---------------------------
# Chat Loop
# ---------------------------
print("Chatbot: Hello! Type 'exit' to quit, 'clear' to clear conversation, 'restart' for a new session, 'show history' to view session history.\n")
temp_history = []

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Chatbot: Ending the conversation. Have a great day!")
        break
    if user_input.lower() == "clear":
        temp_history = []
        os.system("cls" if os.name == "nt" else "clear")
        clear_conversation(session_id)
        print("Chatbot: Conversation cleared! Let's start fresh.")
        continue
    if user_input.lower() == "restart":
        temp_history = []
        restart_session()
        print("Chatbot: Session restarted! Ready for a new conversation.")
        continue
    if user_input.lower() == "show history":
        history = load_messages(session_id)
        if not history:
            print("Chatbot: No messages found for this session.")
        else:
            print("Chatbot: Conversation history:\n")
            for msg in history:
                print(f"{msg['role'].capitalize()}: {msg['content']}")
        continue

    # Save user message
    save_message(session_id, "user", user_input)

    # Load history and summarize if too long
    history = load_messages(session_id)
    if len(history) > SUMMARIZE_AFTER:
        summary_text = summarize_conversation(history[:-10])
        history = [{"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}] + history[-10:]

    history = trim_history(history)

    try:
        response = generate_rag_response(user_input, history)
        print(f"Chatbot: {response}\n")
        save_message(session_id, "assistant", response)
    except APIConnectionError as e:
        print("The server could not be reached")
        print(e.cause)
    except RateLimitError:
        print("A 429 status code was received; please slow down.")
    except APIStatusError as e:
        print("Another non-200-range status code was received")
        print(e.status_code, e.response)
    except Exception as e:
        print("Your code ran into an error")
        print(e)


# AZURE FUNCTION APP ENTRY POINT

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing request for chatbot via Function App")

    try:
        user_message = req.params.get("message")
        command = (user_message or "").lower()
        
        if command == "exit":
            return func.HttpResponse(
                "Chatbot: Ending the conversation. Have a great day!",
                status_code=200
            )
        if command == "clear":
            clear_conversation(session_id)
            return func.HttpResponse("Conversation cleared! Let's start fresh.", status_code=200)

        if command == "restart":
            restart_session()
            return func.HttpResponse(f"Session restarted! Ready for a new conversation. New session ID: {session_id}", status_code=200)

        if command == "show history":
            history = load_messages(session_id)
            if not history:
                return func.HttpResponse("No messages found.", status_code=200)
            text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history])
            return func.HttpResponse(text, status_code=200)

        if not user_message:
            return func.HttpResponse("Chatbot: Hello! How can I assist you today?" 
            " Type 'exit' to end the conversation "
            "or 'clear' to clear the conversation chat "
            "or 'restart' to open a new session " 
            "or 'show history' to see your chat history of this session.\n")

        # Save user message
        save_message(session_id, "user", user_message)

        # Load conversation history
        history = load_messages(session_id)

        

        # Summarize if conversation is very long
        if len(history) > SUMMARIZE_AFTER:
            summary_text = summarize_conversation(history[:-10])
            history = [{"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}] + history[-10:]

        history = trim_history(history)

        generate_rag_response(command, history)

        save_message(session_id, "assistant", response)

        return func.HttpResponse(response)

 
   
    except APIConnectionError as e:
        return func.HttpResponse(f"The server could not be reached: {e.cause}", status_code=503)
    except RateLimitError:
        return func.HttpResponse("A 429 status code was received; please slow down.", status_code=429)
    except APIStatusError as e:
        return func.HttpResponse(
            f"Another non-200-range status code was received: {e.status_code} {e.response}",
            status_code=e.status_code
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return func.HttpResponse(f"Your code ran into an error: {e}", status_code=500)
