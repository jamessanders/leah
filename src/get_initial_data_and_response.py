from config import Config
from call_llm_api import call_llm_api
from urllib.parse import urlparse
import json

def context_template(message: str, context: str) -> str:
    return f"""
context for the query:
{context}

the original query:
{message}

Answer the query based on the context given here, strictly follow the rules given here
"""

def get_initial_data_and_response(message: str, config: Config, history: list, model: str = None) -> tuple:
    """Prepare the initial data, get the response, and rewrite the message."""
    # Use the default persona from config
    persona = "rover"

    script = config.get_prompt_script(persona)
    print(script)
    if script:
        with open("src/prompt_scripts/" + script, "r") as f:
            script_content = f.read()
    else:
        script_content = ""

    message = context_template(message, script_content)

    # Prepare initial data
    initial_data = {
        "model": model if model else config.get_model(persona),
        "temperature": config.get_temperature(persona),
        "messages": [
            {"role": "system", "content": config.get_system_content(persona)}
        ] + [msg for msg in history if msg["role"] != "system"] + [
            {"role": "user", "content": message}
        ],
        "stream": False
    }
    print(initial_data)
    # Call the LLM API with the initial data
    initial_response = call_llm_api(initial_data, config.get_ollama_url(), config.get_headers())
    
    # Process the initial response using 'with' syntax
    with initial_response as response:
        url_response = response.read().decode('utf-8')
        
        # Parse the message from the first choice in the response
        response_data = json.loads(url_response)
        if response_data.get('choices') and response_data['choices'][0].get('message', {}).get('content'):
            parsed_message = response_data['choices'][0]['message']['content']
            return parsed_message
    return message