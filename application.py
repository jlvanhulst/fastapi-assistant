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
from chat import router as chat_router
from fastapi.responses import HTMLResponse
from fastapi import APIRouter

application = FastAPI(title="OpenAI Assistant Runner Demo", version="1.0", debug=config.DEBUG)

application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# this is purely to create a 'ping' health check endpoint feel free to remove.
root_router = APIRouter()
@root_router.get("/", response_class=HTMLResponse)
async def root():
    return "Welcome to the OpenAI Assistant Runner Demo"
application.include_router(root_router)
application.include_router(chat_router)

from twilio_api import router as twilio_router
application.include_router(twilio_router)

# this is the main router for the application
application.include_router(router)
# we just provide a simple endpoint to check if the server is running
