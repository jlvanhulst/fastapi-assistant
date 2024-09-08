"""
This file is responsible for routing the incoming requests to the respective endpoints.
"""

from fastapi.responses import JSONResponse, HTMLResponse
from fastapi import UploadFile

from fastapi import APIRouter
from pydantic import BaseModel

import tools
from typing import Optional
from assistant import Assistant_call, file_upload
import asyncio
router = APIRouter(prefix='/demo')

class AssistantRequest(BaseModel):
    """
    This is the request model for the assistant.
    
    content: str is mandatory and is the prompt for the assistant. In general MORE data is better. 
    file_ids: Optional[list[str]] = None is optional and is a list of file ids to be used by the assistant. 
    when_done: Optional[str] = None is optional and is a function to be called when the assistant is done. 
                               this fumction will receive the thread_id as an argument and can be used to get the full response.
                               and do things like send an email or store the results.
    
    """
    content: str
    file_ids: Optional[list[str]] = None
    when_done: Optional[str] = None
    metadata: Optional[dict] = None

@router.get("/joke", response_class=JSONResponse)
async def assistant_test():
    """
    This is a test endpoint that can be used to test the assistant.
    
    This is the simplest way to 'run' an Assistant. Get the assistant object, provide the name of the Assistant 
    ('test' in this case) and the prompt. 
    """
    assistant = Assistant_call()  
    response = await assistant.newthread_and_run(assistant_name="Joker", content="tell me a joke about sales people")  
    return response

@router.post("/assistant/{assistant_name}", response_class=JSONResponse)
async def run_assistant(assistant_name: str, data: AssistantRequest):
    """
    A simple example endpoint that can be used to call any Assistant with a prompt. give it the name onf the Assisntant in the request and the {"content": "your prompt here"} 
    as the body of the request.
    
    What it returns depends on the settings for that particular Assistant. This can be text or some json if the assistant is set to return json.
    
    """
    
    assistant = Assistant_call()
    return await assistant.newthread_and_run(assistant_name=assistant_name, content=data.content, tools=tools,files=data.file_ids,when_done=data.when_done,metadata=data.metadata)


@router.post("/upload_file", response_class=JSONResponse)
async def create_upload_file(file: UploadFile):    
    """
    This is a test endpoint that expects a form data with the file to be uploaded the OpenAI storage. 
    It can then be used by any Assistant that has access to the OpenAI storage.
    YOU HAVE TO STORE THE FILE_ID if you want to use it in your Assistant call
    
    returns a file object if successful make sure to store the file_id it will be used for further interactions.
    """
    assistant = Assistant_call()
    file_upload = await assistant.uploadfile(file_content=file.file,filename=file.filename)
    return file_upload

@router.get("/assistant_demo", response_class=HTMLResponse)
async def file_demo():
    assistant = Assistant_call()
    
    # uyou can look up the files in the dashboord once they are uploaded
    # https://platform.openai.com/storage/files/
    
    # assistant.uploadfile(file_content=file.file,filename=file.filename)
    # (or use the /sailesdemo/upload_file endpoint to add files)
    
    # this one is an image of chart with some data and the second file is pdf with a report
    files = ['file-QCC8zWDAKgBQKgnrN3D97vku','file-j4hL8oRsiEWQjRJQTbQ85v2k']
    '''
    we are using the Assistant called "Helpful task manager" that is really use a generic Assistant with vision enabled.
    the assistant has access to the files we uploaded and we provide it two very different files. A pdf report and an image of a chart.
    so lets just ask it to create a text version of the data in the image and summarize the report
    and we return html to show the markdown to html option.
    this Assistant and the html response is a path finder to email answering Assistant.
    
    Becasue these are extensive requests and we want to use the data when it is done we supply 'when_done' function
    in that case the return will be just the thread that was created right away the when_done function will receive the thread_id
    Make sure to that the function to call is async!
    '''
    
    result= await assistant.newthread_and_run(assistant_name="Helpful task manager", 
                                              content="Create a text version of the data in this image and summarize the attached pdf report", 
                                              files=files,
                                              when_done=run_after)
    return tools.markdown_to_html(result['response'])


async def run_after(thread_id:str=None):
    '''
    Demo function to show how to pick up after a trhead is done - and then use the results to be stored or further processed.
    '''
    print('Completion call')
    assistant = Assistant_call()
    thread = await assistant.get_thread(thread_id=thread_id)
    print(thread.metadata)
    response = await assistant.getfullresponse(thread_id=thread_id)
    print(response)
    # now that we have the response 