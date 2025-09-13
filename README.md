# Azure AI Chatbot
The Azure AI Chatbot is a console-based application powered by the GPT-4o model on Azure OpenAI. It integrates Retrieval-Augmented Generation (RAG) with Azure Cognitive Search and Document Intelligence to provide context-aware responses from uploaded documents. The bot also includes speech-to-text and text-to-speech capabilities, enabling natural voice interaction. It greets the user, processes input, generates accurate responses enriched with retrieved knowledge, and offers follow-up assistance, demonstrating real-time AI interaction with robust error handling.

## Features
- Powered by GPT-4o with Azure OpenAI  
- Retrieval-Augmented Generation (RAG) using Azure Cognitive Search  
- Document Intelligence integration for knowledge extraction  
- Speech-to-text and text-to-speech for natural voice interaction  
- Cosmos DB for storing user sessions and context  
- Error handling for reliable conversation flow  
- Deployable as an Azure Function App

## Prerequisites

Before setting up the chatbot, ensure you have the following:

- Git installed for cloning the repository  
- An Azure subscription with access to:  
  - Azure OpenAI (for GPT-4o and embeddings)  
  - Azure Cognitive Search (for RAG)  
  - Azure Document Intelligence (for document preprocessing)  
  - Azure Cosmos DB (for storing session data)  
  - Azure Speech Service (to add speech to text and text to speech capabilities)


# Setup

1. Clone this repo:
   ```bash
   git clone https://github.com/Danyabikaram/azure-ai-chatbot.git
   cd azure-ai-chatbot
   
2. Install dependencies:
   pip install -r requirements.txt

3. Set environment variables:
Create a .env file:

   
## API configuration
Add the following environment variables to your .env file:

AZURE_OPENAI_API_KEY=<your_api_key_here>

AZURE_OAI_ENDPOINT<=https://your-endpoint-here.openai.azure.com/>

AZURE_CHAT_DEPLOYMENT="gpt-4o"

AZURE_EMBED_ENDPOINT= <embedded_model_endpoit>

AZURE_EMBED_KEY= <embedded_model_key>

AZURE_EMBED_DEPLOYMENT="text-embedding-3-large"
   
COSMOS_URI = <Your_cosmosDB_URI>

COSMOS_KEY = <Your_Cosmos_DB_Key>

AZURE_SEARCH_ENDPOINT = <your_Azure_Search_Endpoint>

AZURE_SEARCH_KEY = "<Your_Azure_Search_Key>"

AZURE_SEARCH_INDEX = "<Your_Azure_Search_Index_Name>"

AZURE_SEARCH_INDEX= <your_index_name>

AZURE_SEARCH_TEXT_FIELD = "chunk"

AZURE_SEARCH_EMBED_FIELD = "text_vector"

AZURE_BLOB_CONNECTION_STRING = <azure_blob_endpoint>

BLOB_CONTAINER_NAME = <your_blob_container_name>



## Usage example
AI: Hello, I am your AI assistant, here to help you explore Artificial Intelligence. Please feel free to ask me anything related to AI

enter a prompt: what is AI?

AI: Artificial Intelligence (AI) is a field of computer science that focuses on building systems capable of performing tasks that usually require human intelligence.
Would you like me to dive into the types of AI?



## Deploying Python Azure Function App for Chatbot
To deploy the code into a function app in azure, first update your code to the code mentioned in the"__init__.py " file for online use then follow the steps mentioned in the file "Steps to deploy python azure function app for chatbot"

## Architecture
The chatbot uses Azure Functions to handle user input, calls Azure OpenAI for response generation, integrates with Cognitive Search and Document Intelligence for RAG-based context, uses Cosmos DB for session history andleverages Azure Speech Service for speech-to-text and text-to-speech capabilities.


                      













