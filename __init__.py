##To deploy your code into a function app in azure first update your chatbot code to :

import os
import uuid
import tiktoken
import logging
import azure.functions as func
from dotenv import load_dotenv
from openai import AzureOpenAI, APIConnectionError, RateLimitError, APIStatusError
from azure.cosmos import CosmosClient
from azure.cosmos.partition_key import PartitionKey


# Load environment variables
load_dotenv()

# Azure OpenAI and Azure Cognitive Search configuration
azure_oai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_oai_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_oai_deployment = "gpt-4o"
azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
azure_search_key = os.getenv("AZURE_SEARCH_KEY")
azure_search_index = os.getenv("AZURE_SEARCH_INDEX")

try: 
        # Initialize the Azure OpenAI client
    client = AzureOpenAI(
            base_url=azure_oai_endpoint,
            api_key=azure_oai_key,
            api_version="2025-01-01-preview")
except Exception as e:
    print("Your code ran into an error")
    print(f"{e}")
    exit(1)

# Cosmos DB client (Choose storage method: Cosmos DB)
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = "ChatbotDB"
CONTAINER_NAME = "Sessions"

cosmos_client = CosmosClient(COSMOS_URI, COSMOS_KEY)
database = cosmos_client.create_database_if_not_exists(DATABASE_NAME)
container = database.create_container_if_not_exists(
    id=CONTAINER_NAME,
    partition_key=PartitionKey(path="/sessionId")  # partition by session
)


#  Session Management
# Create session identifier
session_id = str(uuid.uuid4())   #generate sessionId
print(f"Your SessionID: {session_id}")  # Can be reused for the same user

#Session restart functionality
def restart_session():
    """Restart the chat session with a new session ID"""
    global session_id    #global var so that i can use it wherever i want
    session_id = str(uuid.uuid4())   # new session ID
    print(f"\n New Session started. Your SessionID: {session_id}\n")
    return session_id

# Implement conversation persistence functions
def save_message(session_id, role, content):
    """Save a message (user or assistant) in Cosmos DB"""
    container.create_item({
        "id": str(uuid.uuid4()),
        "sessionId": session_id,
        "role": role,
        "content": content
    })


def load_messages(session_id):
    """Load all messages for a session from Cosmos DB"""
    query = f"SELECT c.role, c.content FROM c WHERE c.sessionId = '{session_id}' ORDER BY c._ts ASC"
    items = list(container.query_items(query, enable_cross_partition_query=True))
    return [{"role": i["role"], "content": i["content"]} for i in items]


# TOKEN MANAGEMENT 
# Initialize tokenizer (Implement context window management (token limits))
encoding = tiktoken.encoding_for_model("gpt-4o")
# Configurable parameters
MAX_TOKENS = 4000        # safe limit below gpt-4o max
RESERVED_TOKENS = 500    # reserve space for response
SUMMARIZE_AFTER = 25     # when to summarize long chats

def num_tokens_from_messages(messages):
    """Count tokens used by a list of messages."""
    tokens = 0
    for msg in messages:
        tokens += len(encoding.encode(msg["content"]))
    return tokens


def trim_history(history):
    """Ensure history fits within token limit."""
    while num_tokens_from_messages(history) > (MAX_TOKENS - RESERVED_TOKENS):
        if len(history) > 5:
            history.pop(1)  # remove earliest non-system message
        else:
            break
    return history

#  Add summarization for long chats
def summarize_conversation(history):
    """Summarize long conversation history into less than 100 words"""
    summary_prompt = [
        {"role": "system", "content": "Summarize the following conversation in less than 100 words."},
        {"role": "user", "content": str(history)}
    ]
    summary = client.chat.completions.create(
        model="gpt-4o",
        messages=summary_prompt,
        max_completion_tokens=150
    )
    return summary.choices[0].message.content
temp_history = []

#delete function
def clear_conversation(session_id):
    """Delete all messages for a session from Cosmos DB"""
    query = f"SELECT c.id, c.sessionId FROM c WHERE c.sessionId = '{session_id}'"
    items = list(container.query_items(query, enable_cross_partition_query=True))
    for item in items:
        container.delete_item(item["id"], partition_key=item["sessionId"])
    print("Chatbot: Conversation cleared! Let's start fresh.")



# CHAT LOOP (local testing only)
print("Chatbot: Hello! How can I assist you today? Type 'exit' to end the conversation "
"or 'clear' to clear the conversation chat "
"or 'restart' to open a new session " 
"or 'show history' to see your chat history of this session.\n")

# Keep a temporary in-memory history


while __name__ == "__main__":
    user_input = input("You: ")

    #exit
    if user_input.lower() == "exit":
        print("Chatbot: Ending the conversation. Have a great day!")
        break
    

    # Clear session conversation from cosmosdb
    if user_input.lower() == "clear":
        clear_conversation(session_id)
        continue

     # Restart session
    if user_input.lower() == "restart":
        os.system("cls" if os.name == "nt" else "clear")
        restart_session()
        print("Chatbot: Session restarted! Ready for a new conversation.")
        continue

        #show conversation history

    if user_input.lower() == "show history":
    # Load all messages from Cosmos DB for the current session
        history = load_messages(session_id)
        if not history:
            print("Chatbot: No messages found for this session.")
        else:
            print("Chatbot: Here is the conversation history for this session:\n")
            for msg in history:
                print(f"{msg['role'].capitalize()}: {msg['content']}")
        continue

    # Save user message
    save_message(session_id, "user", user_input)

    # Load conversation history
    history = load_messages(session_id)
    print(type(history))
    extension_config = [
        {
            "type": "azure_search",
            "parameters": {
                "endpoint": azure_search_endpoint,     
                "index_name": azure_search_index,      # your index name
                "authentication": {
                    "type": "api_key",
                    "key": azure_search_key,
                },
                "in_scope": False,
            },
        }
    ]

    # Summarize if conversation is very long
    if len(history) > SUMMARIZE_AFTER:
        summary_text = summarize_conversation(history[:-10])  # summarize all except last 10
        history = [{"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}] + history[-10:]

    # Token-based trimming
    history = trim_history(history)

    try:
        # Generate response with context
 
        completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a researcher specialized in AI. "
                    "Always provide detailed and accurate responses "
                    "based on trusted sources such as academic papers and official docs  and docs provided for you using ai search . "
                    "End each response by asking if you can help with anything else."
                )
            }
        ] + history,   #  history includes both user + assistant messages
        max_tokens=500,
        temperature=0.2,
        top_p=0.9,
        presence_penalty=0.6,
        frequency_penalty=0.5,
        extra_body={"data_sources": extension_config}
    )
      
        # Extract assistant reply
        response = completion.choices[0].message.content
        print(f"Chatbot: {response}\n")

        # Save assistant message
        save_message(session_id, "assistant", response)

    # Error Handling
    except APIConnectionError as e:
        print("The server could not be reached")
        print(e.cause)
    except RateLimitError:
        print("A 429 status code was received; please slow down.")
    except APIStatusError as e:
        print("Another non-200-range status code was received")
        print(e.status_code)
        print(e.response)
    except Exception as e:
        print("Your code ran into an error")
        print(f"{e}")



# AZURE FUNCTION APP ENTRY POINT

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing request for chatbot via Function App")

    try:
        user_message = req.params.get("message")
        command = (user_message or "").lower()

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

        extension_config = [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": azure_search_endpoint,
                    "index_name": azure_search_index,
                    "authentication": {"type": "api_key", "key": azure_search_key},
                    "in_scope": False,     #not to only look in the RAG doc
                },
            }
        ]

        # Summarize if conversation is very long
        if len(history) > SUMMARIZE_AFTER:
            summary_text = summarize_conversation(history[:-10])
            history = [{"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}] + history[-10:]

        history = trim_history(history)

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a researcher specialized in AI. Always provide detailed and accurate responses based on trusted sources. End each response by asking if you can help with anything else."}
            ] + history,
            max_tokens=500,
            temperature=0.2,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.5,
            extra_body={"data_sources": extension_config}
        )

        response = completion.choices[0].message.content
        save_message(session_id, "assistant", response)

        return func.HttpResponse(response)

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return func.HttpResponse(f"Error: {e}", status_code=500)




        

    
    
                 
      
       
   
            
       

          









