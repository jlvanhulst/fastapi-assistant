"""
    The entry file for the FastAPI application.
    No need to change anything here use router.py to add new points and functionality
    
    DEBUG setting / OPENAI_API_KEY are read from .env file.
    (see config.py)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import config
from demo import router


app = FastAPI(title="OpenAI Assistant Runner Demo", version="1.0", debug=config.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
    