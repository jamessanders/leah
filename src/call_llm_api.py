import json
import urllib.request
from typing import Any
import socket


def call_llm_api(data: dict, url: str, headers: dict) -> Any:
    """Call the LLM API with the given data, URL, and headers, and return the response."""
    # Convert data to JSON string and encode it
    data = json.dumps(data).encode('utf-8')

    # Create request object
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    return urllib.request.urlopen(req)  # Read timeout 