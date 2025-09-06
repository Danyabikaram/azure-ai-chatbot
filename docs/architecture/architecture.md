# Architecture – V1.0 without function app


## Design Decisions
1.	Use CLI for user interaction 
2.	Reuse the Azure Resource from Lab 1 to avoid duplicating resources.
3.	Deploy GPT-4 in the Azure OpenAI Service to handle natural language queries.
4.	 Keep architecture modular so that additional services can be added in future labs.

## Data Flow
1.	User Input:
   The user types a question or prompt into the Command Line Interface (CLI).
2.	Application Processing:
   The Python CLI Chatbot receives the input and formats it as an API request.
3.	API Request to Azure:
   The chatbot sends the request to the Azure OpenAI Service endpoint using the deployment key and credentials.
4.	AI Response Generation:
   Within the Azure OpenAI Service (inside the Resource Group), the deployed GPT-4o model processes the query and generates a text response.
5.	Response Returned:
   The AI response is sent back from Azure OpenAI to the Python CLI Chatbot.
6.	User Output:
   The chatbot displays the reply in the CLI, completing the interaction loop.



# Architecture – V1.0 with function app

## Design Decisions

1.Use HTTP requests from the user (via browser or CLI tools or Postman) to interact with the chatbot.

2.Deploy chatbot code in an Azure Function App, ensuring it runs in the cloud instead of locally.

3.Reuse the Azure Resource Group and Azure OpenAI resource from Lab 1 to avoid duplicating resources.

4.Deploy GPT-4o in the Azure OpenAI Service to handle natural language queries.

5.Keep the architecture modular and extensible so additional Azure services can be added in future labs.
Data Flow

## Data Flow

1. User Input:
   The user sends an HTTP request with a message to the Azure Function App (via CLI, browser, or API call).

2. Application Processing:
   The Function App (chatbot code) receives the request and prepares an API request.

3. API Request to Azure OpenAI:
   The Function App sends the request to the Azure OpenAI Service using the deployment key and endpoint.

 4. AI Response Generation:
    The deployed GPT-4o model processes the query inside Azure OpenAI and generates a response.

5. Response Returned:
   The response is sent back from Azure OpenAI to the Function App.

6. User Output:
   The Function App returns the AI response to the user via the HTTP response, completing the interaction loop.

# Architecture-V1.1

## Design Decisions

1. Use CLI for user interaction.

2. Reuse the Azure Resource Group from Lab 1 to avoid duplicating resources.

3. Deploy GPT-4o in the Azure OpenAI Service to handle natural language queries.

4. Add Session Management (Azure Cosmos DB) to maintain context across multiple user interactions.

5.Use Azure Blob Storage for storing uploaded documents that will be indexed for RAG.

6.Use Azure Cognitive Search to index documents stored in Blob Storage and provide retrieval for grounding GPT-4o responses.

7. Include Azure Storage (Cosmos DB) for storing logs, conversation history, or analytical data.

8.Keep the architecture modular so that additional services can be integrated in future labs.

## Data Flow

1. User Input: The user types a question or prompt into the Command Line Interface (CLI).

2. Application Processing: The Python CLI Chatbot receives the input and formats it as an API request.

3.  Function App Request: The CLI sends the request to the Azure Function App, which acts as the middleware.

4. Session Management: The Function App checks Azure Cosmos DB to fetch or update the user session state.
   
5. Document Retrieval (RAG) : The Function App queries Azure Cognitive Search, which retrieves relevant document chunks from Blob Storage.
The retrieved context is passed along with the user’s message.

6. AI Request : The Function App sends the processed request to the Azure OpenAI Service (GPT-4o deployment).

7. Response Generation : GPT-4o generates a context-aware response using conversation history and retrieved documents.
   
8. Response Handling: The Function App stores logs or conversation history in Azure Storage (Cosmos DB).

10. Response Returned: The Function App sends the AI-generated response back to the CLI chatbot.

11. User Output: The chatbot displays the reply in the CLI, completing the interaction loop.


# Architecture – V1.2 

## Design Decisions

1.CLI for User Interaction

Users interact with the chatbot via a Command Line Interface (CLI).

2.Reuse Existing Resource Group

Use the Resource Group from Lab 1 to manage all resources efficiently.

3.Azure Blob Storage

Holds the already uploaded documents that form the knowledge base.

4.Azure Document Intelligence

Used during knowledge base preparation to preprocess documents (PDFs, images, handwritten text).

Extracted clean text/structured data from these documents, which was then embedded and indexed in Cognitive Search.

At runtime, the chatbot retrieves documents that were originally processed through Document Intelligence.

5. Azure Cognitive Search (Vector Database)

Stores embeddings generated from Document Intelligence–processed content.

Provides fast similarity search against the knowledge base.

6. Azure OpenAI Service (GPT-4o)

Handles query understanding and response generation.

If no relevant documents are retrieved, it returns: “This information is not in my knowledge.”

7.Azure Cosmos DB

Maintains session state and logs conversation history for continuity.

8.Function App Deployment

Acts as middleware: receives user input from CLI, queries Cognitive Search, manages session, and forwards enriched context to GPT-4o.

## Data Flow

1.User Input (CLI):The user types a question into the CLI chatbot.

2.Application Processing (Function App):The Function App receives the query and generates embeddings for the question.

3.Session Check (Cosmos DB):The Function App retrieves the user’s session history from Cosmos DB to maintain continuity.

4.Document Retrieval (Cognitive Search):
The Function App queries Azure Cognitive Search with the question’s embeddings.

Cognitive Search returns top chunks of documents that were originally extracted and embedded using Document Intelligence.

If no relevant results are found → the Function App sets a fallback flag: “Not in knowledge base.”

5. AI Request (OpenAI GPT-4o):If results exist → user query + retrieved context are passed to GPT-4o for grounded response.
   
6.Response Handling (Cosmos DB):Logs and conversation history are stored in Cosmos DB for future analysis.

7.Response Returned :The Function App sends the final reply back to the CLI chatbot.

8.User Output (CLI):The chatbot displays the grounded response or the fallback “not in knowledge” message.



## Note
This diagram and doc will be updated in later labs .
