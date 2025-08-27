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

4. Add Session Management (Azure Table Storage) to maintain context across multiple user interactions.

5. Include Azure Storage (Cosmos DB) for storing logs, conversation history, or analytical data.

6.Keep the architecture modular so that additional services can be integrated in future labs.

## Data Flow

1. User Input: The user types a question or prompt into the Command Line Interface (CLI).

2. Application Processing: The Python CLI Chatbot receives the input and formats it as an API request.

3. API Request to Azure Function App: The CLI sends the request to the Azure Function App, which acts as the middleware.

4. Session Management: The Function App checks Azure Table Storage to fetch or update the user session state.

5. AI Request to Azure OpenAI: The Function App sends the processed request to the Azure OpenAI Service (GPT-4o deployment).

6. AI Response Generation: The GPT-4o model processes the query inside Azure OpenAI and generates a response.

7. Response Handling: The Function App stores logs or conversation history in Azure Storage (Cosmos DB).

8. Response Returned: The Function App sends the AI-generated response back to the CLI chatbot.

9. User Output: The chatbot displays the reply in the CLI, completing the interaction loop.


## Note
This diagram and doc will be updated in later labs .
