import os
import logging
import azure.functions as func
from dotenv import load_dotenv
from openai import AzureOpenAI, APIConnectionError, RateLimitError, APIStatusError

# Load environment variables locally
load_dotenv()

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-10-21",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# Generate initial welcome message
def get_welcome_message():
    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a helpful assistant. Start by greeting the user."}],
            stream=True
        )
        welcome_text = ""
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                welcome_text += chunk.choices[0].delta.content
        return welcome_text
    except Exception as e:
        logging.error(f"Error generating welcome message: {e}")
        return "Welcome! (unable to generate AI greeting)"

# Azure Function entry point
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing request for chatbot")

    try:
        # If "message" query param is missing, return the welcome message
        user_message = req.params.get("message")
        if not user_message:
            welcome = get_welcome_message()
            return func.HttpResponse(welcome)

        # Check for exit command
        if user_message.strip().lower() == "exit":
            return func.HttpResponse("Chatbot session ended. Goodbye!")

        # Chatbot response
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "always end your answer by asking the user if they want anything else"},
                {"role": "user", "content": user_message}
            ],
            stream=True
        )

        response_text = ""
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                response_text += chunk.choices[0].delta.content

        return func.HttpResponse(response_text)

    # Error handling
    except APIConnectionError:
        return func.HttpResponse("The server could not be reached.", status_code=503)
    except RateLimitError:
        return func.HttpResponse("Rate limit exceeded; please try again later.", status_code=429)
    except APIStatusError as e:
        return func.HttpResponse(f"API error {e.status_code}: {e.response}", status_code=e.status_code)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return func.HttpResponse(f"Unexpected error: {e}", status_code=500)
