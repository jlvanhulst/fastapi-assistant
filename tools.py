import httpx
import html2text
from pydantic import BaseModel, HttpUrl, Field
import logging
import markdown
from assistant import Assistant_call
import sys
def markdown_to_html(md_text):
    '''
    This helper function is used to convert markdown to html.
    It converts the markdown to html and returns the html.
    Handy for openai assistant output that is markdown formatted.
    Args:
        md_text (str): The markdown text to convert to html.
    Returns:
        str: The html content of the markdown text.
    '''
    return markdown.markdown(md_text)

class WebScrapeParameters(BaseModel):
    url: HttpUrl = Field(..., description="The URL of the website to scrape")
    ignore_links: bool = Field(False, description="Ignore links in the text. Use 'False' to receive the URLs of nested pages to scrape.")
    max_length: int = Field(None, description="Maximum length of the text to return")

def html_to_text(html,ignore_links=False,bypass_tables=False,ignore_images=True):
    '''
    This function is used to convert html to text.
    It converts the html to text and returns the text.
    
    Args:
        html (str): The HTML content to convert to text.
        ignore_links (bool): Ignore links in the text. Use 'False' to receive the URLs of nested pages to scrape.
        bypass_tables (bool): Bypass tables in the text. Use 'False' to receive the text of the tables.
        ignore_images (bool): Ignore images in the text. Use 'False' to receive the text of the images.
    Returns:
        str: The text content of the webpage. If max_length is provided, the text will be truncated to the specified length.
    '''
    text = html2text.HTML2Text()
    text.ignore_links = ignore_links
    text.bypass_tables = bypass_tables
    text.ignore_images = ignore_images
    return text.handle(html,)

async def webscrape(plain_json ):
    '''
    This function is used to scrape a webpage.
    It converts the html to text and returns the text.
    
    Args:
        plain_json (dict): The JSON data containing the URL to scrape. It is meant to be called as a tool call from an assistant.
        the json should be in the format of {"url": "https://www.example.com", "ignore_links": False, "max_length": 1000}

    Returns:
        str: The text content of the webpage. If max_length is provided, the text will be truncated to the specified length.
    '''
    info = WebScrapeParameters(**plain_json)
    header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'}
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(str(info.url), headers=header, timeout=5)
    except Exception as e:
        logging.error(f"Failed to fetch URL {info.url}: {e}")
        return ""
    logging.info('succesful webscrape '+str(info.url)+' '+str(response.status_code))
    out = html_to_text(response.text,ignore_links=info.ignore_links)
    if info.max_length:
        return out[0:info.max_length]
    else:
        return out
class company_research_parameters(BaseModel):
    company_name: str = Field(..., description="The name of the company to research")
    website: HttpUrl = Field(..., description="The website of the company to research")

async def company_research(plain_json):
    '''
    Example of how to call an Assisntant as a functions call from another assistant.
    
    Args:
        company_name (str): The name of the company to research
        website (str): The website of the company to research
    Returns:
        str: The response from the assistant.
    '''
    info = company_research_parameters(**plain_json)
    assistant = Assistant_call()
    # the example only has a webscrape but a google search could be added or other options - better to concentrate that inside
    # one deidcated assistant.
    # the cryptic sys.modules[__name__] is used to pass the current module to the assistant
    # maybe it is better to have a 'tools' file per assistant - but we will also use the same functions in different assistants.
    result = await assistant.newthread_and_run(assistant_name="Company Research Assistant", content="Research this company :"+info.company_name+' '+str(info.website), tools=sys.modules[__name__])
    return str(result['response'])

