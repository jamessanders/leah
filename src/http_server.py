import random
from flask import Flask, send_from_directory, request, jsonify, g
import os
from LogManager import LogManager
from NotesManager import NotesManager
from actions import Actions
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
from AuthManager import AuthManager
from functools import wraps
from actions import Actions

app = Flask(__name__)

# Create application context
app_context = app.app_context()
app_context.push()

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')

# Initialize mimetypes
mimetypes.init()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if token is in the Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # If no token in header, check if it's in the request args
        if not token:
            token = request.args.get('token')
            
        if not token:
            return jsonify({"error": "Token is missing"}), 401
            
        # Get username from request args or headers
        username = request.args.get('username') or request.headers.get('X-Username')
        if not username:
            return jsonify({"error": "Username is required for token validation"}), 401
            
        # Validate the token
        auth_manager = AuthManager()
        if not auth_manager.verify_token(username, token):
            return jsonify({"error": "Invalid or expired token"}), 401
            
        # Set username on request state
        g.username = username
        g.token = token
        g.user_config = auth_manager.get_user_config(username, token)
        
        # Set LocalConfigManager on request state
        g.config_manager = LocalConfigManager(username)
            
        # Token is valid, proceed with the request
        return f(*args, **kwargs)
    
    return decorated




# Create a queue to hold the tuples
cleanup_queue = queue.Queue()

# Function to watch the queue and process items
def watch_queue():
    while True:
        try:
            # Wait for 2 minutes
            time.sleep(60)
            # Check if there is an item in the queue
            if not cleanup_queue.empty():
                # Get the item from the queue
                username, persona, parsed_history, full_response = cleanup_queue.get()
                # Process the item
                after_request_cleanup(username, persona, parsed_history, full_response)
        except Exception as e:
            print(f"Error in watch_queue: {e}")

# Start the background thread
threading.Thread(target=watch_queue, daemon=True).start()

voice_files = {}
voice_queue = queue.Queue()

def voice_generator():
    while True:
        try:
            time.sleep(1)
            while not voice_queue.empty():
                voice_filename, plain_text_content, voice = voice_queue.get()
                voice_dir = os.path.join(WEB_DIR, 'voice')
                voice_file_path = os.path.join(voice_dir, voice_filename)
                if not os.path.exists(voice_file_path):
                   print(f"Generating voice for {voice_filename} as {voice_file_path}")
                   async def generate_voice():
                     communicate = edge_tts.Communicate(text=plain_text_content, voice=voice)
                     await communicate.save(voice_file_path)
                   asyncio.run(generate_voice())
                   del voice_files[voice_filename]         
        except Exception as e:
            print(f"Error in voice_generator: {e}")
threading.Thread(target=voice_generator, daemon=True).start()

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


def generate_voice_file(plain_text_content, username, voice, voice_dir):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S"+str(random.randint(0, 1000000)))
    voice_file_path = os.path.join(voice_dir, f'{voice}_{username}_{timestamp}.mp3')
    plain_text_content = strip_markdown(plain_text_content)
    plain_text_content = filter_emojis(plain_text_content)
    plain_text_content = filter_urls(plain_text_content)
    # Remove '#' character
    plain_text_content = plain_text_content.replace('#', '')
    filename = os.path.basename(voice_file_path)
    voice_files[filename] = (plain_text_content, voice)
    voice_queue.put((filename, plain_text_content, voice))
    return filename

def system_message(message: str) -> str:
    json_message = json.dumps({'type': 'system', 'content': message})
    return f"data: {json_message}\n\n"

def memory_template(memories: str) -> str:
    return f"""
Previous notes:

START OF PREVIOUS NOTES
{memories}
END OF PREVIOUS NOTES

Instructions:
Create detailed notes about the conversation and combine them with the previous memories.
Make sure to keep a profile of the user and their interests.
Make sure to keep a profile of your own knowledge, particularily any information about the user.
Make sure to keep a profile of your self and you relationship with the user.
Remove duplicate information.
The final should be a list of instructions for you to follow.
Use a format that is easy for you to use for reference later.
The reply should be no longer than 5000 words.
Don't include any other text than the notes.
"""

def after_request_cleanup(username, persona, parsed_history, full_response):
    # Add any cleanup or logging logic here
    config_manager = LocalConfigManager(username)
    notesManager = config_manager.get_notes_manager()
    memories = notesManager.get_note(f"memories/memories_{persona}.txt")
    if not memories:
        notesManager.put_note(f"memories/memories_{persona}.txt", "No previous notes.")
    memories = notesManager.get_note(f"memories/memories_{persona}.txt")
    parsed_history.append({"role": "assistant", "content": full_response})
    parsed_history = [msg for msg in parsed_history if msg.get('role') != 'system']
    prompt = memory_template(memories)
    persona_override = {
        "system_content": "You are a rigorous and detailed note taker.\n\n" + prompt
    }
    result = ask_agent(persona, "Generate new notes based on the conversation and the previous notes.", conversation_history=parsed_history, persona_override=persona_override)
    notesManager.put_note(f"memories/memories_{persona}.txt", result)
    

@app.route('/query', methods=['POST'])
@token_required
def query():
    data = request.get_json()
    username = g.username
    user_config = g.user_config
    config_manager = LocalConfigManager(g.username)
    original_query = data.get('query', '')
    def generate_stream():    
        # Get the persona from the request, default to 'leah' if not specified
        persona = data.get('persona', 'leah')
        # Assuming config is available in this context
        config = Config()
        personas = config.get_persona_choices(user_config.get("groups", ["default"]))
        if persona not in personas:
            yield system_message("Persona not found")
            yield f"data: {json.dumps({'type': 'end', 'content': 'END OF RESPONSE'})}\n\n"
            return
        use_broker = config.get_use_broker(persona)
        # Extract conversation history from the request
        conversation_history = data.get('history', [])

        # Parse and validate the conversation history
        parsed_history = []
        for entry in conversation_history:
            if isinstance(entry, dict) and 'role' in entry and 'content' in entry:
                parsed_history.append(entry)
            else:
                print(f"Invalid entry in conversation history: {entry}")

        notesManager = config_manager.get_notes_manager()
        memories = notesManager.get_note(f"memories/memories_{persona}.txt")
        if memories:
            memories = "These are your memories from previous conversations: " + memories
        else:
            memories = "You are a helpful assistant that can remember things."

        max_calls = 3
        call_count = 0
        loop_on = True
        while loop_on and call_count < max_calls:  
            call_count += 1
            buffer_mode = False
            check_buffer = ""
            if data.get('context',''):
                data['query'] = context_template(data.get('query', ''), data.get('context', ''), 'User provided context')
                parsed_history[-1]['content'] = data['query']

            # Filter out any system messages from the history
            parsed_history = [msg for msg in parsed_history if msg.get('role') != 'system']
            
            system_content = config.get_system_content(persona)
            if not system_content:
                system_content = ""
            # Prepend persona's system content to the beginning of parsed history
            
            if memories:
                system_content = system_content + "\n\n" + memories
            if use_broker:
                actions = Actions.Actions(config_manager, persona, data.get('query', ''), conversation_history)
                actions_prompt = actions.get_actions_prompt()
                system_content = system_content + "\n\n" + actions_prompt
            
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

            raw_response = ""
            full_response = ""
            buffered_content = ""
            tools = []
            prefix = "```tool_code"
            postfix = "```"
            for chunk in response:
                    try:
                        if isinstance(chunk, str):
                            yield f"data: {json.dumps({'content': chunk})}\n\n"
                            continue
                        else:
                            content = chunk.choices[0].delta.content
                        if content:
                            for character in content:
                                raw_response += character
                                if not buffer_mode and character == prefix[0]:
                                    buffer_mode = True
                                    check_buffer = ""
                                if buffer_mode:
                                    check_buffer = check_buffer + character
                                    if len(check_buffer) >= len(prefix) and not check_buffer.startswith(prefix):
                                        buffer_mode = False
                                        yield f"data: {json.dumps({'content': check_buffer})}\n\n"
                                        buffered_content += check_buffer
                                        full_response += check_buffer
                                        continue
                                    if len(check_buffer) >= len(prefix) and check_buffer.endswith(postfix):
                                        buffer_mode = False
                                        tools.append(check_buffer)
                                        continue
                                    else:
                                        continue
                                else:
                                    buffered_content += character
                                    full_response += character
                                    if buffered_content.endswith(('.', '!', '?')) and len(buffered_content) > 256:
                                        # Generate voice for the complete sentence
                                        voice = config.get_voice(persona)
                                        voice_dir = os.path.join(WEB_DIR, 'voice')
                                        os.makedirs(voice_dir, exist_ok=True)
                                        voice_filename = generate_voice_file(buffered_content, username, voice, voice_dir)
                                        voice_file_info = {
                                            "voice_type": voice,
                                            "filename": voice_filename
                                        }
                                        yield f"data: {json.dumps(voice_file_info)}\n\n"
                                        # Reset the buffer
                                        buffered_content = ""
                                    yield f"data: {json.dumps({'content': character})}\n\n"
                    except json.JSONDecodeError as e:
                        loop_on = False
                        print(f"Error decoding JSON: {e}")

            if buffered_content:
                plain_text_content = strip_markdown(buffered_content)
                voice = config.get_voice(persona)
                voice_dir = os.path.join(WEB_DIR, 'voice')
                os.makedirs(voice_dir, exist_ok=True)
                voice_filename = generate_voice_file(plain_text_content, username, voice, voice_dir)
                voice_file_info = {
                    "voice_type": voice,
                    "filename": voice_filename
                }
                yield f"data: {json.dumps(voice_file_info)}\n\n"
            if tools:
                try:
                    for tool in tools:
                        parsed_response = tool[tool.find(prefix)+len(prefix):].strip()
                        parsed_response = parsed_response[:parsed_response.find(postfix)].strip()
                        parsed_history.append({"role": "assistant", "content": full_response})
                        parsed_response = json.loads(parsed_response.replace(prefix, "").replace(postfix, "").strip()   );
                        tool_name = parsed_response.get("action", "")
                        print("Tool name: " + tool_name)
                        tool_arguments = parsed_response.get("arguments", "{}")
                        if isinstance(tool_arguments, str):
                            tool_arguments = json.loads(tool_arguments)
                        print("Tool arguments: " + str(tool_arguments))
                        log_manager = config_manager.get_log_manager()
                        log_manager.log("tool", tool_name + " " + str(tool_arguments), persona)
                        actions = Actions.Actions(config_manager, persona, data.get('query', ''), parsed_history)
                        for type,message in actions.run_tool(tool_name, tool_arguments):
                            if type == "system":
                                yield f"data: {json.dumps({'type': 'system', 'content': message})}\n\n"
                            elif type == "end":
                                yield f"data: {json.dumps({'type': 'end', 'content': message})}\n\n"
                                loop_on = False
                            elif type == "result":
                                parsed_history = parsed_history[:-1]
                            if len(parsed_history) > 0:
                                parsed_history.pop()
                            parsed_history.append({"role": "user", "content": message})
                            data['query'] = message
                            yield system_message("Query rewritten: " + message)
                except Exception as e:
                    import traceback
                    error_message = f"An error occurred: {str(e)}\n"
                    error_message += traceback.format_exc()
                    print(error_message)
                    yield f"data: {json.dumps({'content': error_message})}\n\n"
                    loop_on = False
            else:
                break

        if call_count >= max_calls:
            yield f"data: {json.dumps({'content': '...'})}\n\n"  
        yield f"data: {json.dumps({'type': 'end', 'content': 'END OF RESPONSE'})}\n\n"

        log_manager = config_manager.get_log_manager()
        log_manager.log_chat("user", original_query, persona)
        log_manager.log_chat("assistant", full_response, persona)
        # Add the current request to the cleanup queue after the response is sent
        add_to_cleanup_queue(username, persona, parsed_history, full_response)


    # Method to add to the queue
    def add_to_cleanup_queue(username, persona, parsed_history, full_response):
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

        cleanup_queue.put((username, persona, parsed_history, full_response))

    return app.response_class(generate_stream(), mimetype='text/event-stream')

@app.route('/voice/<voice_filename>')
def serve_voice(voice_filename):
    voice_dir = os.path.join(WEB_DIR, 'voice')
    voice_file_path = os.path.join(voice_dir, voice_filename)
    if not os.path.exists(voice_file_path):
        plain_text_content, voice = voice_files[voice_filename]
        print(f"Just in time Generating voice for {voice_filename} as {voice_file_path}")
        async def generate_voice():
            communicate = edge_tts.Communicate(text=plain_text_content, voice=voice)
            await communicate.save(voice_file_path)
        asyncio.run(generate_voice())
        del voice_files[voice_filename]
    return send_from_directory(voice_dir, voice_filename)

@app.route('/personas', methods=['GET'])
@token_required
def get_personas():
    config = Config()
    user_config = g.user_config
    if user_config:
        groups = user_config.get("groups", ["default"])
    else:
        groups = ["default"]
    personas = config.get_persona_choices(groups)
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

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    auth_manager = AuthManager()
    token = auth_manager.authenticate(username, password)
    
    if token:
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/protected', methods=['GET'])
@token_required
def protected_route():
    return jsonify({"message": "This is a protected route. You have valid authentication."}), 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001) 