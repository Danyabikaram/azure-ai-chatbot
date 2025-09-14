import sys
sys.path.append('..')
import azure.functions as func
import logging
from session_manager import session_id, restart_session, save_message, load_messages, clear_conversation
from chat_logic import SUMMARIZE_AFTER, trim_history, summarize_conversation, generate_rag_response
from embedding_search import retrieve_relevant_docs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp()

@app.route(route="online-chat", auth_level=func.AuthLevel.ANONYMOUS, methods=['GET', 'POST', 'OPTIONS'])
def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == 'OPTIONS':
        logger.info("Received OPTIONS preflight request")
        return func.HttpResponse('', status_code=200, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

    try:
        req_body = req.get_json()
        logger.info(f"Request body: {req_body}")
        user_input = req_body.get('user_input')
        session_id = req_body.get('session_id')

        if not user_input or not session_id:
            logger.warning("Missing user_input or session_id")
            return func.HttpResponse('{"error": "Missing user_input or session_id"}', status_code=400, mimetype="application/json", headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })

        cmd = user_input.lower()
        logger.info(f"Command received: {cmd}")
        if cmd == "exit":
            return func.HttpResponse('{"response": "Conversation ended"}', mimetype="application/json", headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })
        if cmd == "clear":
            clear_conversation(session_id)
            return func.HttpResponse('{"response": "Conversation cleared"}', mimetype="application/json", headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })
        if cmd == "restart":
            clear_conversation(session_id)
            return func.HttpResponse('{"response": "Session restarted"}', mimetype="application/json", headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })
        if cmd == "show history":
            history = load_messages(session_id)
            if not history:
                resp = "No messages found"
            else:
                resp = "\\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
            return func.HttpResponse(f'{{"response": "{resp}"}}', mimetype="application/json", headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })

        save_message(session_id, "user", user_input)

        history = load_messages(session_id)
        if len(history) > SUMMARIZE_AFTER:
            summary_text = summarize_conversation(history[:-10])
            history = [{"role": "system", "content": f"Summary of earlier conversation: {summary_text}"}] + history[-10:]

        history = trim_history(history)

        relevant_docs = retrieve_relevant_docs(user_input, top_k=3)

        response = generate_rag_response(user_input, history, relevant_docs)

        save_message(session_id, "assistant", response)

        logger.info(f"Response generated: {response}")

        return func.HttpResponse(f'{{"response": "{response}"}}', mimetype="application/json", headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        return func.HttpResponse(f'{{"error": "{str(e)}"}}', status_code=500, mimetype="application/json", headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

@app.route(route="session-id", auth_level=func.AuthLevel.ANONYMOUS, methods=['GET', 'OPTIONS'])
def get_session_id(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == 'OPTIONS':
        logger.info("Received OPTIONS preflight request for session-id")
        return func.HttpResponse('', status_code=200, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
    try:
        from session_manager import session_id as backend_session_id
        logger.info(f"Returning session_id: {backend_session_id}")
        return func.HttpResponse(f'{{"session_id": "{backend_session_id}"}}', mimetype="application/json", headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
    except Exception as e:
        logger.error(f"Exception in get_session_id: {str(e)}")
        return func.HttpResponse(f'{{"error": "{str(e)}"}}', status_code=500, mimetype="application/json", headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

