import random
from flask import Flask, send_from_directory, request, jsonify
import os
from NotesManager import NotesManager
from call_llm_api import ask_agent
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
import threading
import queue
import time
from LocalConfigManager import LocalConfigManager
import dirtyjson

app = Flask(__name__)

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')

# Initialize mimetypes
mimetypes.init()

# Create a queue to hold the tuples
cleanup_queue = queue.Queue()

# Function to watch the queue and process items
def watch_queue():
    while True:
        try:
            # Wait for 2 minutes
            time.sleep(60*5)
            # Check if there is an item in the queue
            if not cleanup_queue.empty():
                # Get the item from the queue
                persona, parsed_history, full_response = cleanup_queue.get()
                # Process the item
                after_request_cleanup(persona, parsed_history, full_response)
        except Exception as e:
            print(f"Error in watch_queue: {e}")

# Start the background thread
threading.Thread(target=watch_queue, daemon=True).start()

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
    """Remove markdown formatting from text."""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]*`', '', text)
    # Remove bold and italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    return text.strip()

def filter_emojis(text: str) -> str:
    """Remove emojis from text."""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub('', text)

def filter_urls(text: str) -> str:
    """Replace URLs with a placeholder text."""
    url_pattern = r'https?://\S+'
    return re.sub(url_pattern, 'URL', text)

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

def generate_voice_file(plain_text_content, voice, voice_dir):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S"+str(random.randint(0, 1000000)))
    voice_file_path = os.path.join(voice_dir, f'response_{timestamp}.mp3')
    plain_text_content = strip_markdown(plain_text_content)
    plain_text_content = filter_emojis(plain_text_content)
    plain_text_content = filter_urls(plain_text_content)
    async def generate_voice():
        communicate = edge_tts.Communicate(text=plain_text_content, voice=voice)
        await communicate.save(voice_file_path)
    asyncio.run(generate_voice())
    return f'response_{timestamp}.mp3'

def system_message(message: str) -> str:
    json_message = json.dumps({'type': 'system', 'content': message})
    return f"data: {json_message}\n\n"

def memory_template(memories: str) -> str:
    return f"""
Previous notes:
{memories}
END OF PREVIOUS NOTES

Prompt:
Create detailed notes about the conversation so and combine them with the previous notes. The reply should be no longer than 1500 words.
"""

def after_request_cleanup(persona, parsed_history, full_response):
    # Add any cleanup or logging logic here
    print(f"Request has been fully processed for persona: {persona} with history: {parsed_history}")
    config_manager = LocalConfigManager("default")
    notesManager = NotesManager(config_manager)
    memories = notesManager.get_note(f"memories_{persona}.txt")
    if not memories:
        notesManager.put_note(f"memories_{persona}.txt", "I am a helpful assistant that can remember things.")
    memories = notesManager.get_note(f"memories_{persona}.txt")
    parsed_history.append({"role": "assistant", "content": full_response})
    parsed_history = [msg for msg in parsed_history if msg.get('role') != 'system']
    prompt = memory_template(memories)
    persona_override = {"system_content": "You are a rigorous and detailed note taker that can remember things."}
    result = ask_agent(persona, prompt, conversation_history=parsed_history, persona_override=persona_override)
    notesManager.put_note(f"memories_{persona}.txt", result)
    

@app.route('/query', methods=['POST'])
def query():
    
    data = request.get_json()
    def generate_stream():    
        system_responses = []
        # Get the persona from the request, default to 'leah' if not specified
        persona = data.get('persona', 'leah')
        # Assuming config is available in this context
        config = Config()
        use_broker = config.get_use_broker(persona)
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

        if use_broker:
            message = ask_agent("broker", data.get('query', ''))
            yield system_message("Broker returned: " + message)
            try:
                if (message.startswith("```json")):
                    message = message[message.find("{"):]
                    message = message[:message.rfind("}")+1]
                json_message = dirtyjson.loads(message)
                if (not json_message['tool'] == "other") and get_agent(json_message['tool']):
                    tool = json_message.get('tool', '')
                    arguments = json_message.get('arguments', [])
                    for result in get_agent(tool)(data.get('query', ''), parsed_history, arguments):
                        if (result[0] == "message"):
                            yield f"data: {json.dumps({'type': 'system', 'content': result[1]})}\n\n"
                        elif (result[0] == "result"):
                            data['query'] = result[1]
                            yield system_message("Agent rewrote query to " + data['query'])
                            parsed_history[-1]['content'] = data['query']
            except Exception as e:
                yield system_message("Broker did not return anything useful: " + str(e))
            
        if data.get('context',''):
            data['query'] = context_template(data.get('query', ''), data.get('context', ''), 'User provided context')
            parsed_history[-1]['content'] = data['query']

        # Filter out any system messages from the history
        parsed_history = [msg for msg in parsed_history if msg.get('role') != 'system']
        # Prepend persona's system content to the beginning of parsed history
        system_content = config.get_system_content(persona)
        if system_content:
            config_manager = LocalConfigManager("default")
            notesManager = NotesManager(config_manager)
            memories = notesManager.get_note(f"memories_{persona}.txt")
            if memories:
                print("Memories: ", memories)
                system_content = system_content + "\n\n" + "These are your notes from previous conversations: " + memories
            else:
                print("No memories found")

        
        
        response = ask_agent(persona, 
                             data.get('query', ''), 
                             stream=True, 
                             conversation_history=parsed_history, 
                             persona_override={"system_content":system_content})

        # Send the conversation history at the end of the stream
        history_info = {
            "type": "history",
            "history": parsed_history
        }
        yield f"data: {json.dumps(history_info)}\n\n"

        for system_response in system_responses:
            yield f"data: {json.dumps({'type': 'system', 'content': system_response})}\n\n"


        full_response = ""
        buffered_content = ""
        for chunk in response:
                try:
                    if isinstance(chunk, str):
                        continue
                    else:
                        content = chunk.choices[0].delta.content
                    if content:
                        buffered_content += content
                        full_response += content
                        # Check if the buffered content ends with a sentence-ending punctuation
                        if buffered_content.endswith(('.', '!', '?')) and len(buffered_content) > 256:
                            # Generate voice for the complete sentence
                            voice = config.get_voice(persona)
                            voice_dir = os.path.join(WEB_DIR, 'voice')
                            os.makedirs(voice_dir, exist_ok=True)
                            voice_filename = generate_voice_file(buffered_content, voice, voice_dir)
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
            voice_dir = os.path.join(WEB_DIR, 'voice')
            os.makedirs(voice_dir, exist_ok=True)
            voice_filename = generate_voice_file(plain_text_content, voice, voice_dir)
            voice_file_info = {
                "voice_type": voice,
                "filename": voice_filename
            }
            yield f"data: {json.dumps(voice_file_info)}\n\n"

        yield f"data: {json.dumps({'type': 'end', 'content': 'END OF RESPONSE'})}\n\n"

        # Add the current request to the cleanup queue after the response is sent
        add_to_cleanup_queue(persona, parsed_history, full_response)

        after_response = config.get_after_response(persona)
        print("After response: ", after_response)

    # Method to add to the queue
    def add_to_cleanup_queue(persona, parsed_history, full_response):
        # Clear all existing items from the cleanup queue
        # Remove existing items for this persona from the cleanup queue
        items = []
        while not cleanup_queue.empty():
            try:
                item = cleanup_queue.get_nowait()
                if item[0] != persona:  # Keep items for other personas
                    items.append(item)
            except queue.Empty:
                break
        # Put back items we want to keep
        for item in items:
            cleanup_queue.put(item)

        cleanup_queue.put((persona, parsed_history, full_response))

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