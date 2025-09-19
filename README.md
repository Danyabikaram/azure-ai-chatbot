# Azure AI Chatbot
The Azure AI Chatbot is a console-based application powered by the GPT-4o model on Azure OpenAI. It integrates Retrieval-Augmented Generation (RAG) with Azure Cognitive Search and Document Intelligence to provide context-aware responses from uploaded documents. The bot also includes speech-to-text and text-to-speech capabilities, enabling natural voice interaction. It greets the user, processes input, generates accurate responses enriched with retrieved knowledge, and offers follow-up assistance, demonstrating real-time AI interaction with robust error handling.

## Features
- Powered by GPT-4o with Azure OpenAI  
- Retrieval-Augmented Generation (RAG) using Azure Cognitive Search  
- Document Intelligence integration for knowledge extraction  
- Speech-to-text and text-to-speech for natural voice interaction  
- Cosmos DB for storing user sessions and context
- Azure Key Vault for secure management of API keys, secrets, and credentials
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
The chatbot uses Azure Functions to handle user input, calls Azure OpenAI for response generation, integrates with Cognitive Search and Document Intelligence for RAG-based context, uses Cosmos DB for session history andleverages Azure Speech Service for speech-to-text and text-to-speech capabilities.


                      













