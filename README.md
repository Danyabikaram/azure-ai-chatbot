# Azure AI Chatbot
The Azure AI Chatbot is a console-based application powered by the GPT-4o model on Azure OpenAI. It combines Retrieval-Augmented Generation (RAG) with Azure Cognitive Search and Document Intelligence to provide context-aware answers from uploaded documents. The bot supports speech-to-text, text-to-speech, and even speech-to-speech interactions, enabling a natural conversational experience. Additionally, it supports function calling to fetch courses and other external data dynamically. The bot greets the user, processes input, retrieves knowledge-enriched responses, and provides follow-up assistance, all with robust error handling and real-time AI interaction.

## Features
Powered by GPT-4o on Azure OpenAI

Retrieval-Augmented Generation (RAG) using Azure Cognitive Search

Integration with Document Intelligence for knowledge extraction

Speech-to-text, text-to-speech, and speech-to-speech for natural voice interaction

Function calling to retrieve information from external sources

Cosmos DB for storing user sessions and context

Azure Key Vault for secure management of API keys and credentials

Robust error handling to ensure reliable conversations

Deployable as an Azure Function App

## Prerequisites

Before setting up the chatbot, ensure you have the following:

- Git installed for cloning the repository  
- An Azure subscription with access to:  
  - Azure OpenAI (for GPT-4o and embeddings)  
  - Azure Cognitive Search (for RAG)  
  - Azure Document Intelligence (for document preprocessing)  
  - Azure Cosmos DB (for storing session data)  
  - Azure Speech Service (to add speech to text and text to speech capabilities)
  -Azure Key Vault (for secure storage and management of secrets, keys, and credentials)


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

AZURE_KEY_VAULT_URL = <your-key-vault-url>



## Usage example
AI: Hello, I am your AI assistant, here to help you explore Artificial Intelligence. Please feel free to ask me anything related to AI

enter a prompt: what is AI?

AI: Artificial Intelligence (AI) is a field of computer science that focuses on building systems capable of performing tasks that usually require human intelligence.
Would you like me to dive into the types of AI?



## Deploying Python Azure Function App for Chatbot
To deploy the code into a function app in azure, follow the steps mentioned in the file "Steps to deploy python azure function app for chatbot" in the terminalof the __init_ file.

## Architecture
The chatbot uses Azure Functions to handle user input, calls Azure OpenAI for response generation, integrates with Cognitive Search and Document Intelligence for RAG-based context, uses Cosmos DB for session history and leverages Azure Speech Service for speech-to-text , text-to-speech capabilities and speech-to-speech interactions.


                      













