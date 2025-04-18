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

def download_and_extract_links(url: str) -> list:
    """Download an HTML page from a URL and extract the links, limited to 1024 tokens."""
    try:
        # Send a request to the URL
        with urllib.request.urlopen(url) as response:
            html = response.read()  
        # Extract links from the content
        links = re.findall(r'<a\b[^>]*>.*?</a>', html.decode('utf-8'))
        # Remove duplicates using a set
        links = list(set(links))
        # Trim the list of links to a maximum of 64
        links = links[:128]
        return html2text.html2text("\n".join(links))
    except Exception as e:
        return []


def download_and_extract_rss(url: str) -> str:
    """Download an RSS feed and convert it to markdown format."""
    try:
        # Send a request to the URL
        with urllib.request.urlopen(url) as response:
            rss_content = response.read()
            
        # Parse the RSS XML
        document = lxml.html.fromstring(rss_content)
        
        # Extract items
        items = document.xpath('//item')
        
        # Build markdown content
        markdown = []
        for item in items:
            # Extract key elements
            title = item.xpath('title/text()')
            title = title[0] if title else ''
            
            link = item.xpath('link/text()')
            link = link[0] if link else ''
            
            description = item.xpath('description/text()')
            description = description[0] if description else ''
            
            pubDate = item.xpath('pubDate/text()')
            pubDate = pubDate[0] if pubDate else ''
            
            # Convert to markdown format
            markdown.append(f"## {title}\n")
            markdown.append(f"*Published: {pubDate}*\n")
            markdown.append(f"{description}\n")
            markdown.append(f"[Read more]({link})\n")
            markdown.append("---\n")
            
        return "\n".join(markdown)
        
    except Exception as e:
        return f"Error downloading or parsing RSS feed: {e}"


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