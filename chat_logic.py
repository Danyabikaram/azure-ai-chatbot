import tiktoken
from openai import RateLimitError
from config import chat_client, CHAT_OAI_CLIENT
from embedding_search import retrieve_relevant_docs

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
# RAG response
# -----------------------------
def generate_rag_response(user_input, history, relevant_docs):
    cache_key = (user_input, tuple(relevant_docs))
    if cache_key in rag_cache:
        return rag_cache[cache_key]

    # Prepare context
    context_text = "\n\n".join(relevant_docs)
    encoding = tiktoken.get_encoding("cl100k_base")
    context_tokens = len(encoding.encode(context_text))
    if context_tokens > MAX_TOKENS // 2:
        context_text = context_text[:MAX_TOKENS // 2]

    system_prompt = (
        "You are an AI assistant specialized in AI. "
        "When the answer exists in the retrieved documents, respond directly without mentioning the documents. "
        "If the answer is not in the documents or not AI-related, say that you are an AI specialist and kindly redirect the user. "
        "Always provide references when possible. After each answer, ask if you can assist with anything else."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"Context from documents:\n{context_text}"}
    ] + history[-10:] + [{"role": "user", "content": user_input}]

    messages = trim_history(messages)

    try:
        response = chat_client.chat.completions.create(
            model=CHAT_OAI_CLIENT,  # ✅ correct: deployment name only
            messages=messages,
            max_tokens=500,
            temperature=0.2,
            top_p=0.9,
            presence_penalty=0.6,
            frequency_penalty=0.5
        )
        result = response.choices[0].message.content
        rag_cache[cache_key] = result
        return result
    except RateLimitError:
        return "I'm currently unable to answer due to rate limiting. Please try again later."
    except Exception as e: 
        return e