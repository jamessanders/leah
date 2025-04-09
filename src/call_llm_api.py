import json
import urllib.request
from typing import Any
import socket
from config import Config
from datetime import datetime
from cache_manager import CacheManager

def context_template(message: str, context: str, extracted_url: str) -> str:
    now = datetime.now()
    today = now.strftime("%B %d, %Y")
    return f"""
Here is some context for the query:
{context}

Source: {extracted_url} (Last updated {today})

Here is the query:
{message}

Answer the query based on the context.
"""

def ask_agent(persona: str, query: str, stream: bool = False) -> str:
    config = Config()
    model = config.get_model(persona)
    system_content = config.get_system_content(persona)
    url = config.get_ollama_url()
    headers = config.get_headers()

    script = config.get_prompt_script(persona)
    if script:
        with open("src/prompt_scripts/" + script, "r") as f:
            script_content = f.read()
            query = context_template(query, script_content, "User provided context")
   
    # Prepare API data with the parsed conversation history
    api_data = {
        "model": model,
        "temperature": config.get_temperature(persona),
        "messages": [{"role": "system", "content": system_content}, {"role": "user", "content": query}],
        "stream": stream
    }
    print("Calling LLM API with: ", api_data)

    if not stream:
        cache = CacheManager()
        cache_key = f"llm_response_{persona}_{query}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response

    try:
        response = call_llm_api(api_data, url, headers)
    except Exception as e:
        print("Error calling LLM API: ", e)
        return "An error occurred while calling the LLM API."
    
    if stream:
        return response
    else:
        result = response.read().decode('utf-8')
        print("Result: ", result)
        final_result = "".join([choice["message"]["content"] for choice in json.loads(result)["choices"]])
        cache.set(cache_key, final_result)
        return final_result

def call_llm_api(data: dict, url: str, headers: dict) -> Any:
    print("Calling LLM API with: ", url, headers)
    """Call the LLM API with the given data, URL, and headers, and return the response."""
    # Convert data to JSON string and encode it
    data = json.dumps(data).encode('utf-8')

    # Create request object
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    return urllib.request.urlopen(req)  # Read timeout 