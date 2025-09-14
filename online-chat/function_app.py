import sys
sys.path.append('..')
import json
import os
import uuid
import azure.functions as func
from azure.cosmos import CosmosClient, PartitionKey
from chat_logic import SUMMARIZE_AFTER, trim_history, summarize_conversation, generate_rag_response
from embedding_search import retrieve_relevant_docs

# Load Cosmos DB config from environment variables
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = "ChatbotDB"
CONTAINER_NAME = "Sessions"

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

app = func.FunctionApp()

@app.route(route="online-chat", auth_level=func.AuthLevel.ANONYMOUS, methods=['GET', 'POST'])
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        user_input = req_body.get('user_input')
        session_id = req_body.get('session_id')

        if not user_input or not session_id:
            return func.HttpResponse(json.dumps({"error": "Missing user_input or session_id"}), status_code=400, mimetype="application/json", headers={'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'})

        cmd = user_input.lower()
        if cmd == "exit":
            return func.HttpResponse(json.dumps({"response": "Conversation ended"}), mimetype="application/json", headers={'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'})
        if cmd == "clear":
            clear_conversation(session_id)
            return func.HttpResponse(json.dumps({"response": "Conversation cleared"}), mimetype="application/json", headers={'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'})
        if cmd == "restart":
            # Assuming restart_session generates a new session, but for simplicity, just clear
            clear_conversation(session_id)
            return func.HttpResponse(json.dumps({"response": "Session restarted"}), mimetype="application/json", headers={'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'})
        if cmd == "show history":
            history = load_messages(session_id)
            if not history:
                resp = "No messages found"
            else:
                resp = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
            return func.HttpResponse(json.dumps({"response": resp}), mimetype="application/json", headers={'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'})

        # Normal chat
        save_message(session_id, "user", user_input)

        history = load_messages(session_id)
        if len(history) > SUMMARIZE_AFTER:
            summary_text = summarize_conversation(history[:-10])
            history = [{"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}] + history[-10:]

        history = trim_history(history)

        relevant_docs = retrieve_relevant_docs(user_input, top_k=3)

        response = generate_rag_response(user_input, history, relevant_docs)

        save_message(session_id, "assistant", response)

        return func.HttpResponse(json.dumps({"response": response}), mimetype="application/json", headers={'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'})

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json", headers={'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'})

@app.route(route="chat", auth_level=func.AuthLevel.ANONYMOUS, methods=['GET'])
def serve_index(req: func.HttpRequest) -> func.HttpResponse:
    try:
        index_path = os.path.join(os.path.dirname(__file__), 'wwwroot', 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return func.HttpResponse(html_content, mimetype="text/html", headers={'Access-Control-Allow-Origin': '*'})
    except Exception as e:
        return func.HttpResponse(f"Error loading index.html: {str(e)}", status_code=500)
