# Azure AI Chatbot

The Azure AI Chatbot provides an interactive console-based conversation using the GPT-4o model on Azure OpenAI. It greets the user, processes input, generates responses, and asks if further assistance is needed. The chat continues until the user types exit, demonstrating real-time AI interaction and error-handling capabilities.

# Setup

## Prerequisites: Set up Azure OpenAI Connection

Go to Azure AI Studio
Click Create new → choose Azure AI Foundry project.
Fill in:
Name: a unique project name
Subscription: your Azure subscription
Resource group: new or existing
Region: must be one of the supported ones for GPT-4o (East US, France Central, Korea Central, West Europe, West US).

Wait for the project to be created.

In the left menu, go to Playgrounds → Chat playground.
In the Setup pane, click + Create a deployment.
Pick From base models → gpt-4o.
Confirm and wait for the deployment.
After deployment:
You can test it in the Chat playground.
You can get your endpoint + API key from Management Center → All Resources → your AI Foundry project.

1. Clone this repo:
   ```bash
   git clone https://github.com/Danyabikaram/azure-ai-chatbot.git
   cd azure-ai-chatbot
   
2. Install dependencies:
   pip install -r requirements.txt

3. Set environment variables:
Create a .env file:
   AZURE_OPENAI_API_KEY=<your_api_key_here>

   AZURE_OPENAI_ENDPOINT<=https://your-endpoint-here.openai.azure.com/>
   

4. Run the chatbot:
python chatbot.py

Type exit to quit.


## API configuration

The chatbot uses your Azure OpenAI resource:

Endpoint: Provided in your Azure resource (example:
https://azureopenai-lab00-eus2-resource.openai.azure.com/)

API Key: Found under Keys and Endpoint in the Azure OpenAI portal

API Version: Currently set to 2024-10-21

Model: gpt-4o 


## Usage example
AI: Hello! How can I assist you today? 👋

enter a prompt: when was google invented?

AI: Google was invented in 1998 by Larry Page and Sergey Brin while they were Ph.D. students at Stanford University in California. Would you like to know more about Google's history or anything else?

enter a prompt: exit

AI: Goodbye!If you have any more questions or need further assistance, feel free to ask. 


## Deploying Python Azure Function App for Chatbot
To deploy the code into a function app in azure, first update your code to the code mentioned in the"__init__.py " file for online use then follow the steps mentioned in the file "Steps to deploy python azure function app for chatbot"

## Prerequisites for RAG deployment

1.Create Azure Resources: Azure Cognitive Search Service – to index and search documents.And an Azure Storage Account – to store your documents.
                         
2.Upload Documents:In your Storage Account, create a Blob Container. Upload all the documents you want the chatbot to use for retrieval.
                   
3.Configure AI Models:In your Azure AI Foundry (previously created), add a Text Embedding Model to GPT-4o.This embedding model will be used for semantic search in your RAG pipeline.
                      
4.Create an Index in Azure Search:Use the embedding model to create a search index. this index will enable the chatbot to retrieve relevant document chunks.


## API configuration
COSMOS_URI = "<Your Cosmos DB URI>"

COSMOS_KEY = "<Your Cosmos DB Key>"

AZURE_SEARCH_ENDPOINT = <your Azure Search Endpoint>

AZURE_SEARCH_KEY = "<Your Azure Search Key>"

AZURE_SEARCH_INDEX = "<Your Azure Search Index Name>"


                                  
