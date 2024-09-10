'''
(C) 2024 Jean-Luc Vanhulst - Valor Ventures 
MIT License

An async assistant class that can be used to interact with the OpenAI Assistant API.

The most basic call is 

result = await assistant.generate(assistant_name=assistant_name, content=data.content)
where assistant_name is the name of the assistant to use and content is the prompt to use.
this will return json with the response, status_code and thread_id

you can also use the assistant_id instead of the assistant_name if you have it.

result = await assistant.generate(assistant_id=assistant_id, content=data.content)

optional parameters are:
    files: list of file_id's to be used by the assistant (the need to be uploaded first)
            Any file that is an image will automatically added to the message to be used for vision
            if the file is 'c', 'cs', 'cpp', 'doc', 'docx', 'html', 'java', 'json', 'md', 'pdf', 'php',
            'pptx', 'py', 'rb', 'tex', 'txt', 'css', 'js', 'sh', 'ts' it will available for retrieval.
            (summarize, extra etc)
            
    when_done: a function to be called when the assistant is done. this function will receive the thread_id as an argument and can be used to get the full response.
               and do things like send an email or store the results.
    If when_done is not provided the function will (await) the result of the assistant call and return the result.
    if when_done is provided the function will return immediately with a "queued" response that includes the thread_id (only)
    this one is useful for api type calls where you want to offload the processing to a background job
    
'''
import asyncio
import json
from openai import AsyncOpenAI as OpenAI
from openai.types.beta import Assistant, Thread
from openai.types.beta.threads.run import Run
import types
from typing import Optional
import logging
from functools import partial
from pydantic import BaseModel, computed_field
import importlib

logger = logging.getLogger(__name__)


async def run_tasks_sequentially(*tasks):
    """
    A helper function that runs async tasks in sequence. 
    be sure to pass partial functions if you need to pass arguments!
    """
    for task in tasks:
        await task()

class Singleton(type):
    """
        metaclass
    """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class file_upload(BaseModel):
    """
    A BaseModel class for handling file uploads to the OpenAI Assistant API.
    This is SIMILAR but not the same as the OpenAI File Object - mostly used to hold the supported file types and their extensions
    and the related ability to be used for vision or retrieval
    
    Attributes:
        file_id: Optional[str] - The ID of the uploaded file.
        filename: str - The name of the file being uploaded.

    Computed Fields:
        extension: str - The file extension extracted from the filename.
        vision: bool - Indicates if the file is an image based on its extension.
        retrieval: bool - Indicates if the file is available for retrieval based on its extension.
    """
    file_id: Optional[str] = None
    filename: str

    
    @computed_field
    def extension(self) -> str:
        return self.filename.split('.')[-1].lower()
    
    @computed_field
    def vision(self) -> bool:
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']
        return self.extension in image_extensions
    @computed_field
    def retrieval(self) -> bool:
        # Determine if the file is for retrieval
        retrieval_extensions = [
            'c', 'cs', 'cpp', 'doc', 'docx', 'html', 'java', 'json', 'md', 'pdf', 'php',
            'pptx', 'py', 'rb', 'tex', 'txt', 'css', 'js', 'sh', 'ts'
        ]
        return self.extension in retrieval_extensions

class Assistant_call( metaclass=Singleton):
    """
    This is the Assistant class which is used to handle thread / runs for the OpenAI Assistant API.
    It is a singleton class which means that only one instance of the class is created and reused.
    It is initialized with the OpenAI client.
    
    (relies on (ONLY) OPENAI_API_KEY to be set in the environment variables)
    """
    def __init__(self) -> None:
        self.client = OpenAI()

    async def get_assistant_by_name(self, assistant_name) -> str|None:
        '''
        This function gets the assistant id for the given assistant name.
        It returns the assistant id if found, otherwise it returns None.
        Note will only search for the first 100 assistants.
        
        Args:
            assistant_name: The name of the assistant to search for.
        Returns:
            The assistant_id if found, otherwise it returns None.
        '''
        assistants =await self.client.beta.assistants.list(
        order="asc",
        limit="100",
        )  
        async for assistant in assistants:
            if assistant.name == assistant_name:
                return assistant.id
        return None
    
    async def get_assistants(self, limit:int=100) -> list[Assistant]:
        assistants =await self.client.beta.assistants.list(
        order="asc",
        limit=limit,
        )  
        return assistants
    async def _when_done_str_to_object(self,when_done:str=None) -> callable:
        """
        This function converts the when_done string to an object.
        If will split the string into module and function name and try to import the function from the module.
        If the function is not found it will try to get it from the globals().
        If the function is not found it will return None.
        """
        if when_done:
            module = None
            func = None
            if '.' in when_done:
                module, func = when_done.rsplit('.', 1)
            try:
                if module:
                    func = getattr(importlib.import_module(module), func)
                else:
                    func = globals().get(when_done)
            except Exception as e:
                logger.error(f"Error in getting function '{when_done}'", e)
                pass
            if not asyncio.iscoroutinefunction(func):
                raise ValueError(f"Provided function '{when_done}' is not found or is not a coroutine")
        return func
        
    async def newthread_and_run(self, assistant_id:str=None, assistant_name:str= None, content:str=None, tools:types.ModuleType=None,metadata:dict={}, files:list=[],when_done:callable=None):
        """
        This is the main function to run a thread for an assistant.
        
        parameters:
            assistant_id: The id of the assistant to use.
            assistant_name: The name of the assistant to use.
            
            use assistant_id OR assistant_name - but not both!
            
            content: The content of the message to send to the assistant. This is what you want to Assistant to process. 
            tools: The tools module to use for the tool calls. You pass a module (.py file) that contains the functions you want to use. 
            Names must match with the function names in the Assistant.
            
            metadata: The metadata to store in the thread.
            The Assistant name is always stored in the metadata as 'assistant_name'
            
            files: The list of file_id's to be used by the assistant.
            these need to be uploaded first. They will be provided as 'vision' if they are images. 
            Otherwise they will be provided as 'file_search' or 'code_interpreter' depending on the file type.
            All files will be available for code interpreter and file search.
            
            when_done: The function to be called when the assistant is done. This must be a coroutine!
                       This function will receive the thread_id as an argument and can be used to get the full response.
                       and do things like send an email or store the results.
                       If when_done is not provided the function will (await) the result of the assistant call and return the result.
                       (Because otherwise the result will never be know :) )
                       if when_done is provided the function will return immediately with a "queued" response that includes the thread_id
                       (only) this one is useful for api type calls where you want to offload the processing to a background job
                       
        returns:
            The response from the assistant.
        """
        if not assistant_id:
            # looking by assistant name
            assistant_id = await self.get_assistant_by_name(assistant_name)
            if not assistant_id:
               return {"response": f"Assistant '{assistant_name}' not found", "status_code": 404}
        vision_files = []
        attachment_files = []
        if files:
            for i in range(len(files)):
                if type(files[i]) == str:
                    files[i] = await self.retrieve_file_object(files[i])
                if files[i].vision:
                    vision_files.append( files[i])
                    continue
                else:
                    attachment_files.append({"file_id": files[i].file_id, "tools": [{"type": "file_search" if files[i].retrieval else "code_interpreter"  }]})     
        thread = await self.get_thread(assistant_name=assistant_name, metadata=metadata) # create a new thread, store assistant name in meta data thread is created if not exists
        await self.client.beta.threads.messages.create(
            thread.id,
            role="user",
            attachments=attachment_files,
            content=content,
        )
        for v in vision_files:
            await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                content= [{
                'type' : "image_file",
                'image_file' : {"file_id": v.file_id ,'detail':'high'}}],
                role="user"
            )  
        if type(when_done) == str:
            when_done = await self._when_done_str_to_object(when_done)
        if when_done:
            
            run = await self.client.beta.threads.runs.create(
                            thread_id=thread.id, 
                            assistant_id=assistant_id)
            
            task1 = partial(self.client.beta.threads.runs.poll,run_id=run.id,thread_id=thread.id,poll_interval_ms=1000)
            task2 = partial(self._process_run,run.id, thread,tools)
            task3 = partial(when_done,thread.id)
            asyncio.create_task( run_tasks_sequentially(task1,task2,task3))
            return {"response": f"thread {thread.id} queued for execution", "status_code": 200, "thread_id": thread.id}
        else:
            run = await self.client.beta.threads.runs.create_and_poll(
                            thread_id=thread.id, 
                            assistant_id=assistant_id, 
                            poll_interval_ms=1000)
            return await self._process_run(run.id, thread,tools)
        return result


    async def get_thread(self, thread_id:str=None, assistant_name:str=None,metadata:dict={}) -> Thread:
        """
        This function either creates a new thread or retrieves an existing thread. 
        If assistant_name is provided, it will store the assistant name in the metadata of the thread.
        If thread_id is provided, it will retrieve the thread.
        
        Args:
            thread_id: The id of the thread to retrieve.
            assistant_name: The name of the assistant to store in the metadata of the thread.
            metadata: The metadata to store in the thread.
        Returns:
            The thread object.
        """
        thread = None
        if metadata==None:
            metadata = {}
        if thread_id:
            try:
                thread = await self.client.beta.threads.retrieve(thread_id)
            except Exception as e:  # pylint: disable=bare-except, broad-except
                logger.error("Error in getting thread", e)
                thread = None
        if not thread:
            if assistant_name:
                metadata["assistant_name"] = assistant_name        
            thread = await self.client.beta.threads.create(
                metadata= metadata,
            )
        return thread

    async def _process_run(self, run_id:str, thread: Thread,tools:types.ModuleType):
        """
        Process run

        Args:
            event: The event to be processed.
            thread: The thread object.
            **kwargs: Additional keyword arguments.

        Raises:
            Exception: If the run fails.
        """
        run = await self.client.beta.threads.runs.retrieve(run_id=run_id, thread_id=thread.id)
        while not run.status in ['completed','expired','failed','cancelled','incomplete']:
            # note this only loops after function calling and possibly next function calling or code interpreter
            if run.status == 'requires_action':
                        
                tool_outputs = await self._process_tool_calls(
                    tool_calls=run.required_action.submit_tool_outputs.tool_calls,
                    tools=tools
                )
                run = await self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs,
                    )

    # RUN STATUS: COMPLETED
        if run.status == "completed":
            response_message = await self.getfullresponse(run.thread_id)
            return {"response": response_message, "status_code": 200, "thread_id": thread.id}

# RUN STATUS: EXPIRED | FAILED | CANCELLED | INCOMPLETE
        if run.status in ['expired','failed','cancelled','incomplete']:
            return {"response": run.last_error, "status_code": 500, "thread_id": thread.id}
        

    async def _process_tool_call(self, tool_call:str, tool_outputs: list, extra_args:dict=None, tools:types.ModuleType=None):
        """
        This function processes a single tool call.
        And also handles the exceptions.
        
        Args:
            tool_call: The tool call to be processed. this is the function name that is going to be called NOTE! must be declared as async!
            tool_outputs: The list of tool outputs.
            extra_args: The extra arguments.
            tools: The tools module to use for the tool calls.
        Returns:
            The tool output.
        """
        result = None
        try:
            arguments = json.loads(tool_call.function.arguments)
            function_name = tool_call.function.name
            if extra_args:
                for key, value in extra_args.items():
                    arguments[key] = value
                                
            #tool_instance keeps track of functions we have already seen
            # load the tool from tools.tools
            to_run = None
            try:
                to_run = getattr(tools, function_name)
            except Exception as e:
                logger.error(f"Error in getting tool {function_name}", e)
                to_run = None
            if to_run is None:
                result = f"Function {function_name} not supported"
            else:
                result = await to_run(arguments)
        except Exception as e:  # pylint: disable=broad-except
            result = str(e)
            logger.error(e)
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": result,
        })

    async def _process_tool_calls(self, tool_calls:list, extra_args:dict=None, tools:types.ModuleType=None):
        """
        This function processes all the tool calls.
        """
        tool_outputs = []
        coroutines = []
        for tool_call in tool_calls:
            coroutines.append(self._process_tool_call(tool_call=tool_call, tool_outputs=tool_outputs, extra_args=extra_args, tools=tools))
        if coroutines:
            await asyncio.gather(*coroutines)
        return tool_outputs


    async def uploadfile(self,file=None,file_content=None,filename=None) -> file_upload:
        ''' Upload a file to openAI either for the Assistant or for the Thread.
        
        parameters:
            file - a file object
            file_content - the content of the file
                        
            filename - the name of the file. If not provided will use the name of the file object
            All uploaded files will automatically be provided in the message to the assistant with both search and code interpreter enabled.
            
        returns:
            file_upload object
        '''
        if file_content == None:
            file_content = await file.read()
        # Determine file extension
        file_upload_object = file_upload(file=file, file_content=file_content, filename=filename)
        
        
        uploaded_file = await self.client.files.create( file=(filename,file_content),purpose=('vision' if file_upload_object.vision else 'assistants'))
        #uploadFile = self.client.files.create( file=(filename,fileContent),purpose='assistants')

        # Append the file information to self._fileids
        return file_upload(file_id=uploaded_file.id, filename=filename, vision=file_upload_object.vision, retrieval=file_upload_object.retrieval)
    
    async def get_response(self, thread_id, remove_annotations:bool=True):
        messages = await self.client.beta.threads.messages.list(thread_id=thread_id)
        message_content = messages.data[0].content[0].text
        # Remove annotations
        if remove_annotations:
           message_content = self._remove_annotations(message_content)

        response_message = message_content.value
        return response_message
    
    def _remove_annotations(self, message_content):
        annotations = message_content.annotations
        for annotation in annotations:
            message_content.value = message_content.value.replace(annotation.text, '')
        return message_content

    async def getlastresponse(self, thread_id:str=None):
        ''' Get the last response from the assistant, returns messages.data[0] 
        '''
        messages = await self.client.beta.threads.messages.list( thread_id=thread_id)
        return messages.data[0]

    async def getallmessages(self, thread_id:str=None) -> list:
        ''' Get all messages from the assistant - returns messages.data (list)
        '''
        messages = await self.client.beta.threads.messages.list( thread_id=thread_id)
        return messages.data

    async def getfullresponse(self, thread_id:str=None, remove_annotations:bool=True) -> str:
        ''' Get the full text response from the assistant (concatenated text type messages)
        traverses the messages.data list and concatenates all text messages
        '''
        messages = await self.client.beta.threads.messages.list( thread_id=thread_id)
        res = ''
        for m in reversed(messages.data):
            if m.role == 'assistant':
                for t in m.content:
                    if t.type == 'text':
                        if remove_annotations:
                            res += self._remove_annotations(t.text).value
                        else:
                            res += t.text.value
                        
        return res

    async def retrievefile(self,file_id:str) -> bytes:
        ''' Retrieve the FILE CONTENT of a file from OpenAI 
        '''
        return await self.client.files.content(file_id=file_id)

    async def retrieve_file_object(self,file_id:str) -> file_upload:
        ''' 
        Retrieve a File  Upload Object of an uploaded file
        This is SIMILAR but not the same as the OpenAI File Object
        '''
        file = await self.client.files.retrieve(file_id=file_id)
        return file_upload(file_id=file.id, filename=file.filename, vision=file.purpose == 'vision', retrieval=file.purpose == 'assistants')
    
    async def transcribe_audio(self,file=None,file_content=None,file_name=None):
        '''
        Transcribe an audio file
        '''
        if file_content == None:
            file_content = await file.read()
        if file_name == None:
            file_name = file.filename
        return await self.client.audio.transcriptions.create(
            model="whisper-1", 
            file=(file_name,file_content)
        )