from datetime import datetime
from typing import List, Dict, Any, Callable
from .IActions import IAction
import urllib.request
import lxml.html
from lxml.html.clean import Cleaner
import html2text
import re

class LinkAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, conversation_history: List[Dict[str, Any]]):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.conversation_history = conversation_history

    def process_query(self) -> Dict[str, Any]:
        # Implement the logic to process the query
        return {
            "response": f"LinkAction processed query: {self.query} with persona: {self.persona}",
            "success": True
        }

    def getTools(self) -> List[tuple]:
        # Return a list of callable tools and their descriptions
        return [
            (self.fetch_link, 
             "fetch_link",
             "Fetches the contents of a url", 
             {"url": "<the url of the link to fetch>"})
        ]
    def context_template(self, message: str, context: str, extracted_url: str) -> str:
        now = datetime.now()
        today = now.strftime("%B %d, %Y")
        return f"""
Here is some context for the query:
{context}

Source: {extracted_url} (Last updated {today})

Here is the query:
{message}

Answer the query using the context provided above.
"""

    def extract_main_content(self, html: bytes, base_url: str) -> str:
        """Extract the main content as markdown from HTML content, using lxml.html.clean."""
        # Parse the HTML content
        document = lxml.html.fromstring(html)
        
        # Use lxml's Cleaner to clean the document
        cleaner = Cleaner()
        cleaner.javascript = True  # Remove JavaScript
        cleaner.style = True       # Remove styles
        cleaner.links = True       # Remove links
        cleaned_content = cleaner.clean_html(document)
        
        # Convert cleaned content to string
        main_content = lxml.html.tostring(cleaned_content, encoding='unicode')
        
        # Remove all links from the content
        main_content = re.sub(r'<a\b[^>]*>.*?</a>', '', main_content)
        
        # Limit the number of tokens to 1024
        tokens = main_content.split()
        print("Tokens: ", len(tokens))
        limited_content = ' '.join(tokens[:150000])
        
        # Convert limited content to markdown
        markdown_content = html2text.html2text(limited_content)
        
        return markdown_content



    def fetch_link(self, arguments: Dict[str, Any]):
        url = arguments['url']
        with urllib.request.urlopen(url) as response:
            html = response.read()
            status_code = response.getcode()
        if status_code != 200:
            yield ("result", self.context_template(self.query, "Error fetching the url", url))
        else:
            yield ("result", self.context_template(self.query, self.extract_main_content(html, url), url))