from openai import APIConnectionError, RateLimitError, APIStatusError
from chat_logic import SUMMARIZE_AFTER, trim_history, summarize_conversation, generate_rag_response
from speech_utils import recognize_speech, synthesize_speech
from config import speech_config
from embedding_search import retrieve_relevant_docs, embedding_cache
from config import COSMOS_KEY , COSMOS_URI
import uuid

# Load Cosmos DB config from environment variables
COSMOS_URI = COSMOS_URI
COSMOS_KEY = COSMOS_KEY
DATABASE_NAME = "ChatbotDB"
CONTAINER_NAME = "Sessions"

# In-memory storage for sessions if Cosmos DB is not configured
sessions = {}
session_id = str(uuid.uuid4())

from azure.cosmos import CosmosClient, PartitionKey
# Initialize Cosmos DB client and container
cosmos_client = CosmosClient(COSMOS_URI, COSMOS_KEY)
database = cosmos_client.create_database_if_not_exists(DATABASE_NAME)
container = database.create_container_if_not_exists(
    id=CONTAINER_NAME,
    partition_key=PartitionKey(path="/sessionId")
)

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
    
def restart_session():
    global session_id
    session_id = str(uuid.uuid4())
    print(f"\nNew Session started. Your SessionID: {session_id}\n")
    return session_id

# Chat Loop
print("Chatbot: Hello! Type 'exit' to quit, 'clear' to clear conversation, 'restart' for a new session, 'show history' to view session history.\n")
print("Type 'voice' to enable voice mode, or press Enter to continue with text mode.\n")

voice_mode = False
response_cache = {}  # cache responses to avoid repeated API calls

mode_input = input("Choose mode (voice/text): ").strip().lower()
if mode_input == "voice":
    voice_mode = True
    print("Voice mode enabled. Speak your queries after the prompt.\n")
else:
    print("Text mode enabled.\n")

while True:
    if voice_mode:
        user_input = recognize_speech(speech_config)
        if user_input is None:
            print("Could not recognize speech. Please try again.")
            continue
        print(f"You (voice): {user_input}")
    else:
        user_input = input("You: ")

    cmd = user_input.lower()
    if cmd == "exit":
        print("Chatbot: Ending the conversation. Have a great day!")
        break
    if cmd == "clear":
        clear_conversation(session_id)
        response_cache.clear()
        print("Chatbot: Conversation cleared! Let's start fresh.")
        continue
    if cmd == "restart":
        restart_session()
        response_cache.clear()
        print("Chatbot: Session restarted! Ready for a new conversation.")
        continue
    if cmd == "show history":
        history = load_messages(session_id)
        if not history:
            print("Chatbot: No messages found for this session.")
        else:
            print("Chatbot: Conversation history:\n")
            for msg in history:
                print(f"{msg['role'].capitalize()}: {msg['content']}")
        continue

    # Use cached response if available
    if user_input in response_cache:
        response = response_cache[user_input]
        print(f"Chatbot: {response}\n")
        if voice_mode:
            synthesize_speech(speech_config, response)
        continue

    save_message(session_id, "user", user_input)

    # Load and summarize history if needed
    history = load_messages(session_id)
    if len(history) > SUMMARIZE_AFTER:
        summary_text = summarize_conversation(history[:-10])
        history = [{"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}] + history[-10:]

    history = trim_history(history)

    try:
        # Retrieve relevant docs (top_k reduced to 3)
       
        relevant_docs = retrieve_relevant_docs(user_input, top_k=3)
     
        print(f"Embedding retrieval successful. Found {len(relevant_docs)} documents.")

        # Generate RAG response using the retrieved docs
        response = generate_rag_response(user_input, history, relevant_docs)
        print(f"Chatbot: {response}\n")

        # Save response and cache it
        save_message(session_id, "assistant", response)
        response_cache[user_input] = response

        if voice_mode:
            synthesize_speech(speech_config, response)

    except APIConnectionError as e:
        print("The server could not be reached")
        print(e.cause)
    except RateLimitError:
        print("Rate limit reached. Try again later.")
    except APIStatusError as e:
        print("Non-200 status code received")
        print(e.status_code, e.response)
    except Exception as e:
        print("Unexpected error:")
        print(e)
