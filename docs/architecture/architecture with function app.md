## Design Decisions
1.Use HTTP requests from the user (via browser or CLI tools or Postman) to interact with the chatbot.

2.Deploy chatbot code in an Azure Function App, ensuring it runs in the cloud instead of locally.

3.Reuse the Azure Resource Group and Azure OpenAI resource from Lab 1 to avoid duplicating resources.

4.Deploy GPT-4o in the Azure OpenAI Service to handle natural language queries.

5.Keep the architecture modular and extensible so additional Azure services can be added in future labs.

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
