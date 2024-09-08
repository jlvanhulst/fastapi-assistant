# AsyncOpenAI Assistant with Function Calling in FastAPI

## Getting Started
I wrote a fairly extensive example of how to use this on (Medium)(https://medium.com/@meeran03/async-streaming-openai-assistant-api-with-function-calling-in-fastapi-0dfe5935f238)

### Dependencies
- Python 3.11 or higher
- FastAPI
- OpenAI API
- aiohttp, httpx for asynchronous HTTP requests

ONLY OPENAI_API_KEY is required.
Will use .env file if present. .env.development file is used for development.
see config.py for the configuration details
Make sure that the OPENAI_API_KEY you select has acceess to the project that the Assistant belong to!

Function calling is handled creating a function with a matching name in the tools.py file.
The function will be call with a JSON dict that corresponds to the arguments of the function definition in the Assisant for the funtion. Now that we have strict typing for the function arguments best practice is to create a 
pydantic class for the arguments and validate the input. See the tools.webscrape function for an example.

Please note that this setup is fully asynchronous and uses the aiohttp library for all HTTP requests.
So evyerting should be async / await.

Proc

### Installing

1. Clone the repository to your local machine.
2. Start Visual Studio Code or Cursor and from the palette select create Environment. Create new venv (select requirements.txt).
You should see the run and debug option right away because launch.json is configured.

### Running the Application
```sh
uvicorn application:application --reload
```

Procfile for Beanstalk already provided as well. So to deploy to Beanstalk:
```sh
eb init
eb create
eb deploy
eb open
```


