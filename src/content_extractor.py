import urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
import lxml.html
from lxml.html.clean import Cleaner
import html2text


def extract_main_content_and_links(html: bytes, base_url: str) -> str:
    """Extract the main content as markdown from HTML content, using lxml.html.clean."""
    # Parse the HTML content
    document = lxml.html.fromstring(html)
    
    # Use lxml's Cleaner to clean the document
    cleaner = Cleaner()
    cleaner.javascript = True  # Remove JavaScript
    cleaner.style = True       # Remove styles
    cleaned_content = cleaner.clean_html(document)
    
    # Convert cleaned content to string
    main_content = lxml.html.tostring(cleaned_content, encoding='unicode')
    
    # Limit the number of tokens to 1024
    tokens = main_content.split()
    print("Tokens: ", len(tokens))
    limited_content = ' '.join(tokens[:150000])
    
    # Convert limited content to markdown
    markdown_content = html2text.html2text(limited_content)
    
    return markdown_content


def download_and_extract_content(url: str) -> tuple:
    """Download an HTML page from a URL and extract the main content, limited to 4048 tokens, and return the HTTP status code."""
    try:
        # Send a request to the URL
        with urllib.request.urlopen(url) as response:
            html = response.read()
            status_code = response.getcode()
            
        if status_code != 200:
            return None, None, status_code
        
        # Extract main content and links
        limited_content = extract_main_content_and_links(html, url)
        
        # Return the limited content and links separately in a tuple
        return limited_content, None, status_code
    except Exception as e:
        return f"Error downloading or parsing content: {e}", None, 404 