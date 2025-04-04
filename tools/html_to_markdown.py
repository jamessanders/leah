#!/usr/bin/env python3

"""
HTML to Plain Text Converter - A script that downloads HTML content from a URL and converts it to plain text.
Usage: python html_to_markdown.py <url>
"""

import sys
import urllib.request
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup

def fetch_html(url):
    """Fetch HTML content from a URL."""
    # Set a custom User-Agent to avoid being blocked
    headers = {
        'User-Agent': 'HTML2Text/1.0'
    }
    
    # Create a request with custom headers
    req = urllib.request.Request(url, headers=headers)
    
    try:
        # Make the request
        with urllib.request.urlopen(req) as response:
            # Read and decode the response
            html_content = response.read().decode('utf-8')
            return html_content
    except HTTPError as e:
        print(f"Error fetching HTML: HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Error fetching HTML: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print("Error: Could not decode the response as UTF-8", file=sys.stderr)
        sys.exit(1)

def convert_to_text(html_content):
    """Convert HTML content to plain text."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Get all text content, preserving whitespace
    text = soup.get_text(separator='\n', strip=True)
    
    # Clean up multiple newlines and filter out short lines
    text = '\n'.join(
        line for line in text.splitlines() 
        if line.strip() and len(line.strip().split()) > 2
    )
    
    return text

def main():
    """Main function to run the script."""
    # Check if a URL was provided
    if len(sys.argv) != 2:
        print("Usage: python html_to_markdown.py <url>", file=sys.stderr)
        sys.exit(1)
    
    # Get the URL from command line arguments
    url = sys.argv[1]
    
    # Fetch the HTML content
    html_content = fetch_html(url)
    
    # Convert to plain text
    text = convert_to_text(html_content)
    
    # Print the text content
    print(text)

if __name__ == "__main__":
    main() 