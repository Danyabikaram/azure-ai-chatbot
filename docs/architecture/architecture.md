# Architecture – Lab 2

![Architecture Diagram](./chatbot-architecture.png)

## Design Decisions
- Keep it minimal: CLI app talking directly to Azure OpenAI (GPT-4o).
- Reuse the Resource Group from Lab 1.
- Simple request/response loop; easy to extend in later labs.

## Data Flow
1.	User Input
o	The user types a question or prompt into the Command Line Interface (CLI).
2.	Application Processing
o	The Python CLI Chatbot receives the input and formats it as an API request.
3.	API Request to Azure
o	The chatbot sends the request to the Azure OpenAI Service endpoint using the deployment key and credentials.
4.	AI Response Generation
o	Within the Azure OpenAI Service (inside the Resource Group), the deployed GPT-4o model processes the query and generates a text response.
5.	Response Returned
o	The AI response is sent back from Azure OpenAI to the Python CLI Chatbot.
6.	User Output
o	The chatbot displays the reply in the CLI, completing the interaction loop.


## Note
This diagram and doc will be updated in later labs .
