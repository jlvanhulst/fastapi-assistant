from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from fastapi import Request

import httpx
from fastapi import Form
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
from typing import Optional
import os
from assistant import Assistant_call
from datetime import datetime
import tools
import asyncio

assistant = Assistant_call()
prefix = '/api/twilio'
router = APIRouter(prefix=prefix)

nummer_thread_list = {} # maps phone number to thread id
# Environment variables for Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

class PhoneUser(BaseModel):
    name: str
    phone: str
    email: str

# Route for handling incoming calls
@router.post('/in', response_class=JSONResponse)
async def incoming_call( request: Request):
    data = await request.form()
    direction = data.get('Direction')
    from_number = data.get('From')
    digits = data.get('Digits')
    '''
    Handle incoming call from Twilio. Decide whether to pick up the call.
    '''
    if direction is None:
        raise HTTPException(status_code=400, detail="No direction in payload")
    if direction == 'inbound':
        user = await lookup_user_by_phone(from_number)
        if user is None:
            response = VoiceResponse()
            response.say("No access to this number. Goodbye.")
            response.hangup()
            return JSONResponse({"status": "error", "response": "User not found"}, status_code=404)
        else:
            email = user.email
            name = user.name
        response = VoiceResponse()
        response.say(f"Hi {name}, this is a bot. How can I help you today?")
        response.record(
            timeout=10, 
            transcribe=False, 
            recording_status_callback=prefix+'/transcribe', 
            recording_status_callback_event='completed'
        )
        return Response(content=str(response), media_type="text/xml")

    elif digits == 'hangup':
        return JSONResponse({"status": "success", "response": "Call ended"}, status_code=200)
    else:
        raise HTTPException(status_code=400, detail="Unknown request")
# Route for handling transcription requests
@router.post('/sms')
async def sms( request: Request):
    data = await request.form()
    from_number = data.get('From')
    message = data.get('Body')
    to_number = data.get('To')
    if from_number not in nummer_thread_list:
        thread = await assistant.get_thread()  
        nummer_thread_list[from_number] = thread.id 
    thread_id = nummer_thread_list[from_number]
    asyncio.create_task(assistant.newthread_and_run(assistant_name="Text responder", 
                                              content=message, 
                                              files=[],tools=tools,metadata={"from":from_number,"to":to_number},
                                              when_done=run_after))
    return JSONResponse({"status": "success", "response": "SMS received"}, status_code=200) 

async def run_after(thread_id:str=None):
    '''
    Demo function to show how to pick up after a trhead is done - and then use the results to be stored or further processed.
    '''
    thread = await assistant.get_thread(thread_id=thread_id)
    from_number = thread.metadata['from']
    to_number = thread.metadata['to']
    message = await assistant.get_response(thread_id=thread_id)
    response = await send_sms(to_number, message,from_number)
    print(response)

async def send_sms(to_number:str, message:str,from_number:str):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        to=to_number,
        from_=from_number,
        body=message
    )
    return message
    
@router.post('/transcribe')
async def incoming_call( request: Request):
    '''
    Fetches the recording, transcribes it using OpenAI, call our dummy run_after.
    '''
    data = await request.form()
    url = data.get('RecordingUrl')
    callId = data.get('CallSid')
    from_number = await get_caller_phone_number(callId)
    user = await lookup_user_by_phone(from_number)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Error fetching recording")
    date = datetime.now().strftime("%Y-%m-%d")
    # Create transcription with OpenAI's Whisper model
    transcription = await assistant.transcribe_audio(file_content=response.content, file_name='voiceail from {from_number} {date}.wav' )
    
    # Sending transcription via email
    respond2voicemail.delay(transcription.text, user['email'], user['name'])
    
    return JSONResponse({"status": "success", "response": "Transcription received"}, status_code=200)

# Async user lookup
# Async user lookup
async def lookup_user_by_phone(phone_number: str) -> PhoneUser:
    '''
    Lookup a user by phone number; if not found, return None.
    Simulated as a static lookup here, but you can replace with actual database logic.
    '''
    return PhoneUser(name="John Doe", phone=phone_number, email="john.doe@example.com")

# Async function to get the caller's phone number from Twilio
async def get_caller_phone_number(call_sid: str) -> str:
    '''
    Fetch caller phone number using Twilio Client.
    '''
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    call = client.calls(call_sid).fetch()
    return call._from


async def respond2voicemail(msg, from_email, from_name):
    # process a single unread email from vicbot@valor
    meta =  {"from": from_email, "subject":"voicemail response" , "files":[] }
    response = await assistant.newthread_and_run(assistantName="Voicemail Responder", metadata = meta, 
    content = ("Answer this voicemail from "+from_name+">> "+msg))
    return response