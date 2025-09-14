import uuid
import json
import os

# Directory for session files
SESSIONS_DIR = "sessions"
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

# Initialize session
session_id = str(uuid.uuid4())
print(f"Your SessionID: {session_id}")

def restart_session():
    global session_id
    session_id = str(uuid.uuid4())
    print(f"\nNew Session started. Your SessionID: {session_id}\n")
    return session_id

def save_message(session_id, role, content):
    session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    messages = []
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            messages = json.load(f)
    messages.append({
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content
    })
    with open(session_file, 'w') as f:
        json.dump(messages, f, indent=4)

def load_messages(session_id):
    session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(session_file):
        return []
    with open(session_file, 'r') as f:
        messages = json.load(f)
    return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

def clear_conversation(session_id):
    session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(session_file):
        os.remove(session_file)
