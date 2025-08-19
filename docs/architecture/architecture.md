# Architecture – Lab 2


## Design Decisions
•	Use CLI for user interaction 
•	Reuse the Azure Resource Group from Lab 1 to avoid duplicating resources.
•	Deploy GPT-4o in the Azure OpenAI Service to handle natural language queries.
•	Keep architecture modular so that additional services can be added in future labs.


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
6.	User Output
   The chatbot displays the reply in the CLI, completing the interaction loop.


## Note
This diagram and doc will be updated in later labs .
