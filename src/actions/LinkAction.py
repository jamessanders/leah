from datetime import datetime
from typing import List, Dict, Any, Callable
from .IActions import IAction
import lxml.html
from lxml.html.clean import Cleaner
import html2text
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import requests

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

    def addition_notes(self) -> str:
        return " - You can fetch any URL from the internet.  Always use the fetch_link tool to fetch the contents of a URL."

    def getTools(self) -> List[tuple]:
        # Return a list of callable tools and their descriptions
        return [
            (self.fetch_link_with_selenium, 
             "fetch_url",
             "Downloads the contents of a url.  Used to fetch content of urls", 
             {"url": "<the url of the page to fetch>"})
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
        cleaner.links = False       # Remove links
        cleaned_content = cleaner.clean_html(document)
        
        # Convert cleaned content to string
        main_content = lxml.html.tostring(cleaned_content, encoding='unicode')
                
        # Limit the number of tokens to 1024
        tokens = main_content.split()
        print("Tokens: ", len(tokens))
        limited_content = ' '.join(tokens[:15000])
        
        # Convert limited content to markdown
        markdown_content = html2text.html2text(limited_content)
        
        return markdown_content

    def fetch_link(self, arguments: Dict[str, Any]):
        try:
            url = arguments['url']
            response = requests.get(url)
            status_code = response.status_code
            html = response.content
            if status_code != 200:
                yield ("result", self.context_template(self.query, "Error fetching the url", url))
            else:
                yield ("result", self.context_template(self.query, self.extract_main_content(html, url), url))
        except Exception as e:
            yield ("result", self.context_template(self.query, "Error fetching the url", url))

    def fetch_link_with_selenium(self, arguments: Dict[str, Any]):
        try:
            url = arguments['url']
            
            # Set up Selenium WebDriver with Chrome
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run headless Chrome
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # Initialize the WebDriver
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Fetch the URL
            driver.get(url)
            
            # Attempt to find the main content section
            main_content_element = None
            try:
                main_content_element = driver.find_element(By.TAG_NAME, 'main')
            except:
                try:
                    main_content_element = driver.find_element(By.TAG_NAME, 'article')
                except:
                    try:
                        main_content_element = driver.find_element(By.CLASS_NAME, 'content')
                    except:
                        main_content_element = driver.find_element(By.TAG_NAME, 'body')
            
            # Extract the page source from the main content
            html = main_content_element.get_attribute('innerHTML')
            
            # Close the WebDriver
            driver.quit()
            
            # Extract main content
            main_content = self.extract_main_content(html.encode('utf-8'), url)
            
            yield ("result", self.context_template(self.query, main_content, url))
        except Exception as e:
            yield ("result", self.context_template(self.query, "Error fetching the url with Selenium", url))
