import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import uuid
import azure.functions as func
import logging
from config import COSMOS_URI , COSMOS_KEY
from config import build_realtime_ws_url
from chat_logic import SUMMARIZE_AFTER, trim_history, summarize_conversation, generate_rag_response
from embedding_search import retrieve_relevant_docs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Cosmos DB config from environment variables
COSMOS_URI = COSMOS_URI
COSMOS_KEY = COSMOS_KEY
DATABASE_NAME = "ChatbotDB"
CONTAINER_NAME = "Sessions"

# In-memory storage for sessions if Cosmos DB is not configured
sessions = {}


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


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        path = req.route_params.get('path', '').strip('/')
        logger.info(f"Request path: {path}")
        if req.method == 'OPTIONS':
            logger.info("Received OPTIONS preflight request")
            return func.HttpResponse('', status_code=200, headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })

        if path == 'online-chat':
            if req.method == 'GET':
                action = req.params.get('action')
                if action == 'sessions':
                    try:
                        query = "SELECT DISTINCT c.sessionId FROM c"
                        items = list(container.query_items(query, enable_cross_partition_query=True, max_item_count=1000))
                        sessions = []
                        for item in items:
                            session_id = item['sessionId']
                            # Get first message as title
                            first_msg_query = f"SELECT TOP 1 c.content FROM c WHERE c.sessionId = '{session_id}' AND c.role = 'user' ORDER BY c._ts ASC"
                            first_msgs = list(container.query_items(first_msg_query, enable_cross_partition_query=True))
                            title = first_msgs[0]['content'][:20] + '...' if first_msgs else 'Untitled'
                            sessions.append({"id": session_id, "title": title})
                        return func.HttpResponse(json.dumps({"sessions": sessions}), mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                    except Exception as e:
                        logger.error(f"Error fetching sessions: {e}")
                        return func.HttpResponse(json.dumps({"error": "Failed to fetch sessions"}), status_code=500, mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                elif action == 'history':
                    session_id = req.params.get('session_id')
                    if not session_id:
                        return func.HttpResponse(json.dumps({"error": "Missing session_id"}), status_code=400, mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                    try:
                        history = load_messages(session_id)
                        history_formatted = [{"text": msg["content"], "isUser": msg["role"] == "user"} for msg in history]
                        return func.HttpResponse(json.dumps({"history": history_formatted}), mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                    except Exception as e:
                        logger.error(f"Error fetching history: {e}")
                        return func.HttpResponse(json.dumps({"error": "Failed to fetch history"}), status_code=500, mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                else:
                    session_id = str(uuid.uuid4())
                    logger.info(f"Generated session_id: {session_id}")
                    return func.HttpResponse(json.dumps({"session_id": session_id}), mimetype="application/json", headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })
            elif req.method == 'POST':
                req_body = req.get_json()
                logger.info(f"Request body: {req_body}")
                user_input = req_body.get('user_input')
                session_id = req_body.get('session_id')

                if not user_input or not session_id:
                    logger.warning("Missing user_input or session_id")
                    return func.HttpResponse(json.dumps({"error": "Missing user_input or session_id"}), status_code=400, mimetype="application/json", headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })

                cmd = user_input.lower()
                logger.info(f"Command received: {cmd}")
                if cmd == "exit":
                    return func.HttpResponse(json.dumps({"response": "Conversation ended"}), mimetype="application/json", headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })
                if cmd == "clear":
                    try:
                        clear_conversation(session_id)
                        return func.HttpResponse(json.dumps({"response": "Conversation cleared"}), mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                    except Exception as e:
                        logger.error(f"Error clearing conversation: {e}")
                        return func.HttpResponse(json.dumps({"error": "Failed to clear conversation"}), status_code=500, mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                if cmd == "restart":
                    try:
                        clear_conversation(session_id)
                        return func.HttpResponse(json.dumps({"response": "Session restarted"}), mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                    except Exception as e:
                        logger.error(f"Error restarting session: {e}")
                        return func.HttpResponse(json.dumps({"error": "Failed to restart session"}), status_code=500, mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                if cmd == "show history":
                    try:
                        history = load_messages(session_id)
                        if not history:
                            resp = "No messages found"
                        else:
                            resp = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
                        return func.HttpResponse(json.dumps({"response": resp}), mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })
                    except Exception as e:
                        logger.error(f"Error loading history: {e}")
                        return func.HttpResponse(json.dumps({"error": "Failed to load history"}), status_code=500, mimetype="application/json", headers={
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'
                        })

                try:
                    save_message(session_id, "user", user_input)
                except Exception as e:
                    logger.error(f"Error saving user message: {e}")
                    return func.HttpResponse(json.dumps({"error": "Failed to save message"}), status_code=500, mimetype="application/json", headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })

                try:
                    history = load_messages(session_id)
                    if len(history) > SUMMARIZE_AFTER:
                        summary_text = summarize_conversation(history[:-10])
                        history = [{"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}] + history[-10:]

                    history = trim_history(history)

                    relevant_docs = retrieve_relevant_docs(user_input, top_k=3)

                    response = generate_rag_response(user_input, history, relevant_docs)

                    save_message(session_id, "assistant", response)

                    logger.info(f"Response generated: {response}")

                    return func.HttpResponse(json.dumps({"response": response}), mimetype="application/json", headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })
                except Exception as e:
                    logger.error(f"Error generating response: {e}")
                    return func.HttpResponse(json.dumps({"error": "Failed to generate response"}), status_code=500, mimetype="application/json", headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })

        elif path == 'get_realtime_session':
            if req.method == 'GET':
                try:
                    deployment = req.params.get('deployment')
                    api_version = req.params.get('api_version')
                    ws_url = build_realtime_ws_url(deployment=deployment, api_version=api_version)
                    return func.HttpResponse(json.dumps({"url": ws_url}), mimetype="application/json", headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })
                except Exception as e:
                    logger.error(f"Error building realtime WS URL: {e}")
                    return func.HttpResponse(json.dumps({"error": "Failed to get realtime session"}), status_code=500, mimetype="application/json", headers={
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    })
            else:
                return func.HttpResponse("Method not allowed", status_code=405)

        elif path == 'session-id':
            if req.method == 'GET':
                session_id = str(uuid.uuid4())
                logger.info(f"Returning session_id: {session_id}")
                return func.HttpResponse(json.dumps({"session_id": session_id}), mimetype="application/json", headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                })
            else:
                return func.HttpResponse("Method not allowed", status_code=405)

        elif path == 'chat':
            if req.method == 'GET':
                try:
                    index_path = os.path.join(os.path.dirname(__file__), 'index.html')
                    logger.info(f"Attempting to load index.html from: {index_path}")
                    with open(index_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    logger.info("Successfully loaded index.html")
                    return func.HttpResponse(html_content, mimetype="text/html", headers={'Access-Control-Allow-Origin': '*'})
                except Exception as e:
                    logger.error(f"Exception in serve_index: {str(e)}", exc_info=True)
                    return func.HttpResponse(f"Error loading index.html: {str(e)}", status_code=500)
            else:
                return func.HttpResponse("Method not allowed", status_code=405)

        else:
            logger.warning(f"Unknown route path: {path}")
            return func.HttpResponse("Not Found", status_code=404)

    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json", headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
