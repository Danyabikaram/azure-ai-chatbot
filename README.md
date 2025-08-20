# Azure AI Chatbot

A simple chatbot using **Azure OpenAI GPT-4**.

## Setup

1. Clone this repo:
   ```bash
   git clone https://github.com/Danyabikaram/azure-ai-chatbot.git
   cd azure-ai-chatbot
   
2. Install dependencies:
   pip install -r requirements.txt

3. Set environment variables:
Create a .env file:
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint-here.openai.azure.com/

4. Run the chatbot:
python chatbot.py

Type exit to quit.


## API configuration

The chatbot uses your Azure OpenAI resource:

Endpoint: Provided in your Azure resource (example:
https://azureopenai-lab00-eus2-resource.openai.azure.com/)

API Key: Found under Keys and Endpoint in the Azure OpenAI portal

API Version: Currently set to 2024-10-21

Model: gpt-4 (or gpt-4o if available)

Configuration is handled in chatbot.py using environment variables.


## Usage example
AI: Hello! How can I assist you today? 👋

enter a prompt: when was google invented?
AI: Google was invented in 1998 by Larry Page and Sergey Brin while they were Ph.D. students at Stanford University in California. Would you like to know more about Google's history or anything else?

enter a prompt: exit
AI: Goodbye!If you have any more questions or need further assistance, feel free to ask. 
