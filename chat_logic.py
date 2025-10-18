import tiktoken
from openai import RateLimitError
from config import chat_client, CHAT_OAI_CLIENT
from embedding_search import retrieve_relevant_docs
import json
import httpx
from bs4 import BeautifulSoup

MAX_TOKENS = 4096
SUMMARIZE_AFTER = 100

# Simple caches
summary_cache = {}
rag_cache = {}

# -----------------------------
# Token counter
# -----------------------------
def num_tokens_from_messages(messages, model="gpt-4o"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0
    for message in messages:
        for _, value in message.items():
            num_tokens += len(encoding.encode(value))
    return num_tokens

# -----------------------------
# Trim history if too long
# -----------------------------
def trim_history(history):
    total_tokens = num_tokens_from_messages(history, model="gpt-4o")
    while total_tokens > MAX_TOKENS and len(history) > 1:
        history.pop(0)
        total_tokens = num_tokens_from_messages(history, model="gpt-4o")
    return history

# -----------------------------
# Summarization
# -----------------------------
def summarize_conversation(history):
    conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    if conversation_text in summary_cache:
        return summary_cache[conversation_text]

    messages = [
        {"role": "system", "content": "Summarize the following conversation briefly."},
        {"role": "user", "content": conversation_text}
    ]

    try:
        response = chat_client.chat.completions.create(
            model=CHAT_OAI_CLIENT,  # deployment name, not endpoint
            messages=messages,
            max_tokens=150,
            temperature=0.3
        )
        summary = response.choices[0].message.content
        summary_cache[conversation_text] = summary
        return summary
    except RateLimitError:
        return "Summary unavailable due to rate limiting."

# -----------------------------
# Function calling: get_course_recommendations
# -----------------------------
def get_course_recommendations(query):
    courses = []

    # Scrape Coursera
    coursera_url = f"https://www.coursera.org/search?query={query}"
    try:
        response = httpx.get(coursera_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        course_cards = soup.find_all('a', href=True)
        for card in course_cards:
            href = card['href']
            if '/learn/' in href or '/specializations/' in href:
                name = card.get_text(strip=True)
                if name:
                    courses.append({"name": name, "url": f"https://www.coursera.org{href}", "platform": "Coursera"})
                if len(courses) >= 3:
                    break
    except Exception as e:
        print(e) 

    if not courses:
        return "No courses found for your query."

    result = "Here are some courses I found:\n"
    for course in courses[:5]:
        result += f"- {course['name']} ({course['platform']}): {course['url']}\n"
    return result

import json
from difflib import SequenceMatcher

def is_topic_related_to_documents(query_topic: str, documents: list, threshold: float = 0.001108) -> bool:
    """
    Check if the query topic is semantically related to any retrieved document.
    This uses simple fuzzy matching. You can replace this with embeddings for better accuracy.
    """
    for doc in documents:
        similarity = SequenceMatcher(None, query_topic.lower(), doc.lower()).ratio()
        print(f"Similarity between '{query_topic}' and document: {similarity}")
        if similarity > threshold:
            print(f"Similarity between '{query_topic}' and document: {similarity}")
            return True
    return False

# -----------------------------
# RAG response with function calling
# -----------------------------
def generate_rag_response(user_input, history, relevant_docs):
    cache_key = (user_input, tuple(relevant_docs))
    if cache_key in rag_cache:
        return rag_cache[cache_key]

    # Check if the user input is related to the documents
    if not is_topic_related_to_documents(user_input, relevant_docs):
        return "No additional information available."

    # Prepare context
    context_text = "\n\n".join(relevant_docs)
    encoding = tiktoken.get_encoding("cl100k_base")
    context_tokens = len(encoding.encode(context_text))
    if context_tokens > MAX_TOKENS // 2:
        context_text = context_text[:MAX_TOKENS // 2]

    system_prompt = (
        "You are an AI assistant specialized in AI. "
        "When the answer exists in the retrieved documents, respond directly without mentioning the documents. "
        "If the user asks about learning a topic that is related to the documents, use the get_course_recommendations function. "
        "If the topic is unrelated, politely say the topic is outside the current scope. "
        "Always provide references when possible. After each answer, ask if you can assist with anything else."
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_course_recommendations",
                "description": "Get course recommendations based on a query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for courses, e.g., 'python'"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"Context from documents:\n{context_text}"}
    ] + history[-10:] + [{"role": "user", "content": user_input}]

    messages = trim_history(messages)

    try:
        response = chat_client.chat.completions.create(
            model=CHAT_OAI_CLIENT,
            messages=messages,
            max_tokens=500,
            temperature=0.2,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.5,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message
        result = message.content or ""

        # Check if the model decided to call the course tool
        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "get_course_recommendations":
                    args = json.loads(tool_call.function.arguments)
                    query = args.get("query", "")

                    # Check if the query is relevant to retrieved docs
                    if is_topic_related_to_documents(query, relevant_docs):
                        course_response = get_course_recommendations(query)
                        result += "\n\n" + course_response
                    else:
                        result += "\n\nThe topic you're asking about doesn't match the topics found in the current documents, so I can't recommend courses on that."

        rag_cache[cache_key] = result
        return result

    except RateLimitError:
        return "I'm currently unable to answer due to rate limiting. Please try again later."
    except Exception as e:
        return str(e)
