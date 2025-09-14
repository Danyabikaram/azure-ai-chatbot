from openai import APIConnectionError, RateLimitError, APIStatusError
from session_manager import session_id, restart_session, save_message, load_messages, clear_conversation
from chat_logic import SUMMARIZE_AFTER, trim_history, summarize_conversation, generate_rag_response
from speech_utils import recognize_speech, synthesize_speech
from config import speech_config
from embedding_search import retrieve_relevant_docs, embedding_cache

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
