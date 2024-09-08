# OpenAI Assistant with Function Calling in FastAPI

## Getting Started

### Dependencies

- Python 3.11 or higher
- FastAPI
- OpenAI API
- aiohttp, httpx for asynchronous HTTP requests

Refer to `requirements.txt` for a complete list of dependencies.

Will use .env file if present. .env.development file is used for development.
See config.py for more details.

At this point only OPENAI_API_KEY is required. 
Make sure that the OPENAI_API_KEY you select has acceess to the project that the Assistant ID's belong to.

Function calling is by creating a function with a matching name in the tools.py file.
The function will be call with a JSON dict that corresponds to the arguments of the function definition in the Assisant for the funtion. Now that we have strict typing for the function arguments best practice is to create a 
pydantic class for the arguments and validate the input. See the webscrape function for an example.

Please note that this setup is fully asynchronous and uses the aiohttp library for all HTTP requests.
So evyerting should be async / await.


### Installing

1. Clone the repository to your local machine.
2. Create a virtual environment:

```sh
python -m venv env
```

3. Activate the virtual environment:

- On Windows:

```sh
env\Scripts\activate
```

- On Unix or MacOS:

```sh
source env/bin/activate
```

4. Install the required packages:

```sh
pip install -r requirements.txt
```

### Configuration

- Ensure you have valid API keys for OpenAI and OpenWeather APIs set in your `.env` file.

### Running the Application

1. Start the application:

```sh
uvicorn main:app --reload
```


