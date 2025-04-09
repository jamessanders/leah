from flask import Flask, send_from_directory, request, jsonify
import os
from call_llm_api import call_llm_api
from config import Config
import json
import edge_tts
import asyncio
from datetime import datetime
import re
import mimetypes
import copy
from content_extractor import download_and_extract_content
from urllib.parse import urlparse
from get_initial_data_and_response import get_initial_data_and_response
from agents import get_agent

app = Flask(__name__)

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')

# Initialize mimetypes
mimetypes.init()

@app.route('/')
def serve_index():
    return send_from_directory(WEB_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    # Get the MIME type based on the file extension
    mime_type, _ = mimetypes.guess_type(filename)
    
    # Special case for JavaScript files
    if filename.endswith('.js'):
        mime_type = 'text/javascript'
    # If no MIME type is found, default to 'application/octet-stream'
    elif mime_type is None:
        mime_type = 'application/octet-stream'
    
    # Serve the file with the correct MIME type
    return send_from_directory(WEB_DIR, filename, mimetype=mime_type)

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

def system_message(message: str) -> str:
    json_message = json.dumps({'type': 'system', 'content': message})
    return f"data: {json_message}\n\n"

@app.route('/query', methods=['POST'])
def query():

    def getAnAgent(query: str) -> str:
        if not query or not isinstance(query, str):
            return None
        agent_mention_pattern = r'^@([a-zA-Z0-9_]+)'
        agent_mentions = re.findall(agent_mention_pattern, query)
        if not agent_mentions:
            return None
        valid_agents = [get_agent(mention) for mention in agent_mentions]
        return valid_agents
    
    data = request.get_json()
    def generate_stream():    
        system_responses = []
        # Get the persona from the request, default to 'leah' if not specified
        persona = data.get('persona', 'leah')
        # Assuming config is available in this context
        config = Config()
        
        # Extract conversation history from the request
        conversation_history = data.get('history', [])
        print("Conversation history: ", conversation_history)

        
        # Parse and validate the conversation history
        parsed_history = []
        for entry in conversation_history:
            if isinstance(entry, dict) and 'role' in entry and 'content' in entry:
                parsed_history.append(entry)
            else:
                print(f"Invalid entry in conversation history: {entry}")

        if not getAnAgent(data.get('query', '')):
            agent = get_agent("broker")   
            for type, message in agent(data.get('query', ''), parsed_history):
                if type == "message":
                    yield system_message(message)
                elif type == "result":
                    data['query'] = message
                    print("Broker rewrote query to " + data['query'])
                    print(message)
                    yield system_message("Broker rewrote query to " + data['query'])
                    break

        while True:
            valid_agents = getAnAgent(data.get('query', ''))
            if not valid_agents:
                break
            print(f"Valid agents found in query: {valid_agents}")
            print("The query is: " + data.get('query', ''))
            for result in valid_agents[0](re.sub(r'^@[a-zA-Z]+', '', data.get('query', '')), parsed_history):
                if (result[0] == "message"):
                    yield f"data: {json.dumps({'type': 'system', 'content': result[1]})}\n\n"
                elif (result[0] == "result"):
                    data['query'] = result[1]
                    system_responses.append("Agent rewrote query to " + data['query'])
                    parsed_history[-1]['content'] = data['query']
                    yield "data: {json.dumps({'type': 'system', 'content': 'Rovers resport: '" + result[1] + "})}\n\n"

        if data.get('context',''):
            data['query'] = context_template(data.get('query', ''), data.get('context', ''), 'User provided context')
            parsed_history[-1]['content'] = data['query']

        # Filter out any system messages from the history
        parsed_history = [msg for msg in parsed_history if msg.get('role') != 'system']
        # Prepend persona's system content to the beginning of parsed history
        system_content = config.get_system_content(persona)
        if system_content:
            parsed_history.insert(0, {"role": "system", "content": system_content})

        
        # Prepare API data with the parsed conversation history
        api_data = {
            "model": config.get_model(persona),
            "temperature": config.get_temperature(persona),
            "messages": parsed_history,
            "stream": True
        }
        
        print("Calling LLM API with data: ", api_data)
    
        response = call_llm_api(api_data, config.get_ollama_url(), config.get_headers())

        # Send the conversation history at the end of the stream
        history_info = {
            "type": "history",
            "history": parsed_history
        }
        yield f"data: {json.dumps(history_info)}\n\n"

        for system_response in system_responses:
            yield f"data: {json.dumps({'type': 'system', 'content': system_response})}\n\n"

        buffered_content = ""
        for line in response:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                try:
                    chunk = json.loads(line[6:])
                    if isinstance(chunk, str):
                        print("Chunk is a string: ", chunk)
                        continue
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

@app.route('/personas', methods=['GET'])
def get_personas():
    config = Config()
    personas = config.get_persona_choices()
    return jsonify(personas)

@app.route('/avatars/<requested_avatar>')
def serve_avatar(requested_avatar):
    img_dir = os.path.join(WEB_DIR, 'img')
    default_avatar = 'avatar.png'
    # Check if the requested avatar exists
    if os.path.exists(os.path.join(img_dir, requested_avatar)):
        return send_from_directory(img_dir, requested_avatar)
    else:
        return send_from_directory(img_dir, default_avatar)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001) 