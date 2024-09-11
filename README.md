# AsyncOpenAI Assistant with Function Calling in FastAPI

## Getting Started
I wrote a fairly extensive example of how to use this on (Medium)(https://medium.com/@jlvalorvc/a-scalable-async-openai-assistant-processor-built-with-fastapi-sourcecode-on-github-67fc757e9832)

### Dependencies
- Python 3.11 or higher
- FastAPI
- OpenAI API
- aiohttp, httpx for asynchronous HTTP requests

ONLY OPENAI_API_KEY is required
Will use .env file if present. .env.development file is used for development.
see config.py for the configuration details
Make sure that the OPENAI_API_KEY you select has acceess to the project that the Assistant belong to!

Function calling is handled by creating an async function with a matching name in the tools.py file.
The function will be call with a JSON dict that corresponds to the arguments of the function definition in the Assisant for the funtion. Now that we have strict typing for the function arguments best practice is to create a 
pydantic class for the arguments and validate the input. See the tools.webscrape function for an example.

Please note that this setup is fully asynchronous and uses the aiohttp library for all HTTP requests.
So evyerting should be async / await.

### Installing

1. Clone the repository to your local machine.
2. Start Visual Studio Code or Cursor and from the palette select create Environment. Create new venv (select requirements.txt).
You should see the run and debug option right away because launch.json is configured.

You can try out 127.0.0.1:8000 this should just say "Welcome to the OpenAI Assistant runner"
If you get OPENAI_API_KEY error create a .env file and add the OPENAI_API_KEY and restart.

Next try 127.0.0.1/demo/list_assistants

or go to 127.0.0.1/chat/ to chat with assistant. You should be able to select assistant and ask questions - and upload a file. This is an easy way to test your Assistnat like in the playground
but with function calling already enabled. The chats Assistant will always use 'import tools' to 
use for the Assistant function calls.

### Running the Application (if not through vscode)
```sh
uvicorn application:application --reload
```

Procfile for Beanstalk already provided as well. So to deploy to Beanstalk:
```sh
eb init
eb create (pick Python 3.11, Looadbalancer: Aplliction )
eb deploy
eb open
```


version 1.1.0 
- added /chat to easyly chat with assistants and be able to upload files.

