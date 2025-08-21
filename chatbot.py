import os
from dotenv import load_dotenv
from openai import AzureOpenAI, APIConnectionError, RateLimitError, APIStatusError
load_dotenv()

###client initialization
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-10-21",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
###	Welcome message using AI

completion = client.chat.completions.create(
      model="gpt-4", 
      messages=[
        {"role": "system", "content": "You are a helpful assistant. Start by greeting the user by greeting him. "},
      ],
      stream=True
    )

for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='',)
print('\n')   

# message handling and response generating
while True:
  
  try:

    inp = input('enter a prompt:' )

    # this completion will handle the chatting part and asking at the end if any frther assisstant is required
    completion = client.chat.completions.create(
      model="gpt-4", 
      messages=[
        {"role": "system", "content": "always end your answer by asking the user if he want anything else"},
        {"role": "user", "content": inp}
      ],
      stream=True
    )

    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='',)
    print('\n')   


    # handle exit command
    
    if inp.strip().lower() == "exit":
      break

  ### error handling

  except APIConnectionError as e:
      print("The server could not be reached")
      print(e._cause_)  # an underlying Exception, likely raised within httpx.
  except RateLimitError as e:
      print("A 429 status code was received; we should back off a bit.")
  except APIStatusError as e:
      print("Another non-200-range status code was received")
      print(e.status_code)
      print(e.response)
  except Exception as e:
     print("your code ran into an error \n")
     print(f"{e}")
