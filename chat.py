
from fastapi.responses import JSONResponse, HTMLResponse,StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import UploadFile

from fastapi import APIRouter
from pydantic import BaseModel

import tools
from typing import Optional
from assistant import Assistant_call, file_upload
import asyncio
import logging
from assistant import stream_generator, Assistant_call, AssistantRequest
import tools

assistant = Assistant_call()
logger = logging.getLogger(__name__)

router    = APIRouter(prefix='/chat')
templates = Jinja2Templates(directory="templates")
chats = {}

@router.post("/thread/{chat_id}")
async def get_chat_response(chat_id: str, data: AssistantRequest):
    """
    called from javascript when the user sends a message - if the thread_id is not in the list of chats, a new chat is created
    """
    assistant_id = None
    if data.content == "":
        return ""
    if chat_id not in chats:
        thread = await assistant.get_thread()   
        chats[chat_id] = thread.id
    if data.assistant_id and not data.assistant_id == "":
        assistant_id = data.assistant_id
    response =assistant.stream_thread(thread_id=chats[chat_id],assistant_id=assistant_id,assistant_name="Chatbot",content=data.content,tools=tools)
    return StreamingResponse(stream_generator(response))

@router.get("/", response_class=JSONResponse)
async def chat_frontend(request: Request):
    """
    This function renders the chat frontend
    """
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/upload/{chat_id}",response_class=JSONResponse)
async def upload_file(chat_id: str, file: UploadFile):
    """
    This function uploads a file to the assistant
    """
    file_upload = await assistant.uploadfile(file_content=file.file,filename=file.filename)
    if chat_id not in chats:
        thread = await assistant.get_thread()   
        chats[chat_id] = thread.id
    await assistant.prep_thread(thread_id=chats[chat_id],files=[file_upload],content=f"file {file.filename} uploaded")
    return {"status": "success", "message": "File uploaded successfully"}

@router.get("/get_assistants",response_class=JSONResponse)
async def get_assistants():
    """
    This function gets the assistants from the assistant
    """
    assistants = await assistant.get_assistants()
    data = []
    async for a in assistants:
        data.append({"assistant_id":a.id,"assistant_name":a.name})
    return {"status": "success", "message": "File uploaded successfully","data":data}
