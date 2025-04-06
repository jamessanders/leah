import urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re


def extract_main_content_and_links(html: bytes, base_url: str) -> tuple:
    """Extract the main content and links from HTML content."""
    # Parse the HTML content
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract the main content (e.g., from <main> or <body> tags)
    main_content = soup.find('main') or soup.find('body')
    
    # Get text content
    if main_content:
        text_content = main_content.get_text(separator=' ', strip=True)
        # Remove content within square brackets
        text_content = re.sub(r'\[.*?\]', '', text_content)
        
        # Limit the number of tokens to 1024
        tokens = text_content.split()
        limited_content = ' '.join(tokens[:7000])
        
        # Extract all links with text from the main content and ensure they are fully qualified
        links = [f"<a href='{urljoin(base_url, a['href'])}'>{a.get_text(strip=True)}</a>" for a in main_content.find_all('a', href=True) if a.get_text(strip=True)]
        
        # Limit the number of links to 32
        links = links[:256]
        
        return limited_content, links
    else:
        return "No main content found.", []


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
        limited_content, links = extract_main_content_and_links(html, url)
        
        # Return the limited content and links separately in a tuple
        return limited_content, links, status_code
    except Exception as e:
        return f"Error downloading or parsing content: {e}", None, 404 