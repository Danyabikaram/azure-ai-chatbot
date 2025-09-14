import tiktoken
from openai import RateLimitError
from config import chat_client, AZURE_OAI_DEPLOYMENT
from embedding_search import retrieve_relevant_docs

MAX_TOKENS = 4096
SUMMARIZE_AFTER = 100

# Simple caches to reduce repeated API calls
summary_cache = {}
rag_cache = {}

def num_tokens_from_messages(messages, model=AZURE_OAI_DEPLOYMENT):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        for _, value in message.items():
            num_tokens += len(encoding.encode(value))
    return num_tokens

def trim_history(history):
    total_tokens = num_tokens_from_messages(history)
    while total_tokens > MAX_TOKENS and len(history) > 1:
        history.pop(0)
        total_tokens = num_tokens_from_messages(history)
    return history

def summarize_conversation(history):
    conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    # Check cache first
    if conversation_text in summary_cache:
        return summary_cache[conversation_text]

    messages = [
        {"role": "system", "content": "Summarize the following conversation briefly."},
        {"role": "user", "content": conversation_text}
    ]

    try:
        response = chat_client.chat.completions.create(
            model=AZURE_OAI_DEPLOYMENT,
            messages=messages,
            max_tokens=150,
            temperature=0.3
        )
        summary = response.choices[0].message.content
        summary_cache[conversation_text] = summary
        return summary
    except RateLimitError:
        # Graceful fallback instead of retry
        return "Summary unavailable due to rate limiting."

def generate_rag_response(user_input, history, relevant_docs):
    # Check cache
    cache_key = (user_input, tuple(relevant_docs))
    if cache_key in rag_cache:
        return rag_cache[cache_key]

    # Prepare context (truncate if too long)
    context_text = "\n\n".join(relevant_docs)
    context_tokens = len(tiktoken.encoding_for_model(AZURE_OAI_DEPLOYMENT).encode(context_text))
    if context_tokens > MAX_TOKENS // 2:
        context_text = context_text[:MAX_TOKENS // 2]  # hard truncate to fit budget

    system_prompt = (
        "You are an AI specialized assistant. "
        "Only answer based on the retrieved documents. "
        "If the answer is not in the documents, say 'I don't know'. "
        "Explain details briefly and provide references. "
        "Do not use your general knowledge. "
        "After each answer, ask if you can assist with anything else."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"Context from documents:\n{context_text}"}
    ] + history[-10:] + [{"role": "user", "content": user_input}]

    # Trim history again if needed
    messages = trim_history(messages)

    try:
        response = chat_client.chat.completions.create(
            model=AZURE_OAI_DEPLOYMENT,
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
        # Graceful fallback instead of retry
        return "I'm currently unable to answer due to rate limiting. Please try again later."
