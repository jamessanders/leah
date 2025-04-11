import json
import urllib.request
from typing import Any
import socket
from config import Config
from datetime import datetime
from cache_manager import CacheManager
from openai import OpenAI

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

def ask_agent(persona: str, query: str, stream: bool = False, conversation_history: list[dict] = [], should_cache: bool = False, persona_override: dict = {}) -> str:
    config = Config()
    model = persona_override.get("model", config.get_model(persona))
    system_content = persona_override.get("system_content", config.get_system_content(persona))
    url = persona_override.get("url", config.get_ollama_url(persona))
    headers = persona_override.get("headers", config.get_headers())
    api_key = persona_override.get("api_key", config.get_ollama_api_key(persona))
    script = persona_override.get("script", config.get_prompt_script(persona))
    if script:
        with open("src/prompt_scripts/" + script, "r") as f:
            script_content = f.read()
            query = context_template(query, script_content, "User provided context")
   
    # Filter out system messages from conversation history
    filtered_history = [msg for msg in conversation_history if msg.get('role') != 'system']
    messages = [{"role": "system", "content": system_content}, *filtered_history, {"role": "user", "content": query}]
    
    # Prepare API data with filtered conversation history
    api_data = {
        "model": model,
        "temperature": config.get_temperature(persona),
        "messages": messages,
        "stream": stream
    }
    print("Calling LLM API with: ", api_data)

    if not stream and should_cache:
        cache = CacheManager()
        cache_key = f"llm_response_{persona}_{query}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response

    try:
        response = call_llm_with_openai(api_data, url, headers, api_key)
    except Exception as e:
        print("Error calling LLM API: ", e)
        return "An error occurred while calling the LLM API."
    
    if stream:
        return response
    else:
        result = response.choices[0].message.content
        print("Result: ", result)
        if should_cache:
            cache.set(cache_key, result)
        return result

def call_llm_with_openai(data: dict, url: str, headers: dict, api_key = None) -> Any:
    print("Calling LLM API with (Using OpenAI): ", url, headers)
    print("DATA: ", data)
    api_key = api_key or "lm-studio"
    client = OpenAI(api_key=api_key, base_url=url)
    return client.chat.completions.create(  
        model=data["model"],
        messages=data["messages"],
        temperature=data["temperature"],
        stream=data["stream"]
    );

def call_llm_api(data: dict, url: str, headers: dict) -> Any:
    print("Calling LLM API with: ", url, headers)
    """Call the LLM API with the given data, URL, and headers, and return the response."""
    # Convert data to JSON string and encode it
    data = json.dumps(data).encode('utf-8')

    # Create request object
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    return urllib.request.urlopen(req)  # Read timeout 