from flask import Flask, send_from_directory, request, jsonify
import os
from call_llm_api import call_llm_api
from config import Config
import json
import edge_tts
import asyncio
from datetime import datetime
import re
from content_extractor import download_and_extract_content
from urllib.parse import urlparse

app = Flask(__name__)

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')

@app.route('/')
def serve_index():
    return send_from_directory(WEB_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory(WEB_DIR, filename)

# Function to strip markdown
def strip_markdown(text):
    # Remove markdown links
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove other markdown syntax
    text = re.sub(r'[_*`]', '', text)
    return text

def check_for_urls(message: str) -> tuple[bool, str]:
    """
    Check if a message contains any URLs and return the first URL found.
    
    Args:
        message (str): The message to check for URLs
        
    Returns:
        tuple[bool, str]: A tuple containing (has_url, extracted_url)
            - has_url (bool): True if a URL was found, False otherwise
            - extracted_url (str): The first URL found, or None if no URL was found
    """
    url_pattern = r'https?://\S+'
    url_matches = re.findall(url_pattern, message)
    has_url = len(url_matches) > 0
    extracted_url = url_matches[0] if has_url else None
    return has_url, extracted_url

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

def generate_voice_file(plain_text_content, voice, voice_dir, timestamp):
    voice_file_path = os.path.join(voice_dir, f'response_{timestamp}.mp3')
    async def generate_voice():
        communicate = edge_tts.Communicate(text=plain_text_content, voice=voice)
        await communicate.save(voice_file_path)
    asyncio.run(generate_voice())
    return f'response_{timestamp}.mp3'

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    print(data)
    # Use the persona 'emily'
    persona = 'emily'
    # Assuming config is available in this context
    config = Config()
    
    # Extract conversation history from the request
    conversation_history = data.get('history', [])
    print(conversation_history)

    # Parse and validate the conversation history
    parsed_history = []
    for entry in conversation_history:
        if isinstance(entry, dict) and 'role' in entry and 'content' in entry:
            parsed_history.append(entry)
        else:
            print(f"Invalid entry in conversation history: {entry}")

    # Check if the user's query contains a URL
    has_url, extracted_url = check_for_urls(data.get('query', ''))
    if has_url:
        print(f"Grabbing context from: {extracted_url}")
        limited_content, links, status_code = download_and_extract_content(extracted_url)
        if status_code == 200:
            # Use context template to rewrite the query message
            data['query'] = context_template(data['query'], limited_content, extracted_url)
            # Update the last item in the history with the rewritten query
            if parsed_history:
                parsed_history[-1]['content'] = data['query']
        else:
            print("Failed to fetch content from the URL")

    # Add system message to the beginning of the conversation history
    parsed_history.insert(0, {"role": "system", "content": config.get_system_content(persona)})

    # Prepare API data with the parsed conversation history
    api_data = {
        "model": config.get_model(persona),
        "temperature": config.get_temperature(persona),
        "messages": parsed_history,
        "stream": True
    }
    
    response = call_llm_api(api_data, config.get_ollama_url(), config.get_headers())
    
    def generate_stream():
        buffered_content = ""
        for line in response:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                try:
                    chunk = json.loads(line[6:])
                    if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                        content = chunk['choices'][0]['delta']['content']
                        buffered_content += content
                        # Check if the buffered content ends with a sentence-ending punctuation
                        if buffered_content.endswith(('.', '!', '?')) and len(buffered_content) > 256:
                            # Generate voice for the complete sentence
                            plain_text_content = strip_markdown(buffered_content)
                            voice = config.get_voice(persona)
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            voice_dir = os.path.join(WEB_DIR, 'voice')
                            os.makedirs(voice_dir, exist_ok=True)
                            voice_filename = generate_voice_file(plain_text_content, voice, voice_dir, timestamp)
                            voice_file_info = {
                                "voice_type": voice,
                                "filename": voice_filename
                            }
                            yield f"data: {json.dumps(voice_file_info)}\n\n"
                            
                            # Reset the buffer
                            buffered_content = ""
                        yield f"data: {json.dumps({'content': content})}\n\n"
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")

        # After the loop, check for any remaining buffered content
        if buffered_content:
            plain_text_content = strip_markdown(buffered_content)
            voice = config.get_voice(persona)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            voice_dir = os.path.join(WEB_DIR, 'voice')
            os.makedirs(voice_dir, exist_ok=True)
            voice_filename = generate_voice_file(plain_text_content, voice, voice_dir, timestamp)
            voice_file_info = {
                "voice_type": voice,
                "filename": voice_filename
            }
            yield f"data: {json.dumps(voice_file_info)}\n\n"

    return app.response_class(generate_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(port=8001) 