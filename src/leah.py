#!/usr/bin/env python3

"""
Leah - A Python script for processing messages and generating text-to-speech responses.
This script interacts with an LMStudio API for message processing and edge-tts for voice synthesis.
"""

import argparse
import asyncio
import contextlib
import edge_tts
import io
import json
import os
import re
import sys
import textwrap
import tempfile
import threading
import queue
import urllib.request
from typing import Dict, Any
from copy import deepcopy
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

# Suppress pygame output
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame


class Config:
    """Configuration management class for the Leah script."""
    
    def __init__(self):
        """Initialize the configuration by loading from config.json."""
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json and merge with .hey.config.json if it exists."""
        # Load the main config file
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Check for user config in home directory
        home_dir = os.path.expanduser("~")
        user_config_path = os.path.join(home_dir, '.hey.config.json')
        
        if os.path.exists(user_config_path):
            try:
                with open(user_config_path, 'r') as f:
                    user_config = json.load(f)
                
                # Merge user config with main config
                config = self._merge_configs(config, user_config)
            except Exception as e:
                pass
        
        return config
    
    def _merge_configs(self, main_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config with main config, with user config taking precedence."""
        # Create a deep copy of the main config to avoid modifying it
        merged_config = deepcopy(main_config)
        
        # Merge top-level keys
        for key, value in user_config.items():
            if key not in merged_config:
                merged_config[key] = value
            elif isinstance(value, dict) and isinstance(merged_config[key], dict):
                # Recursively merge dictionaries
                merged_config[key] = self._merge_configs(merged_config[key], value)
            else:
                # User config takes precedence
                merged_config[key] = value
        
        return merged_config
    
    def _get_persona_config(self, persona='default') -> Dict[str, Any]:
        """Get the configuration for a persona, merging with default if needed."""
        if persona == 'default':
            return self.config['personas']['default']
        
        # Start with a deep copy of the default persona
        persona_config = deepcopy(self.config['personas']['default'])
        
        # Merge in the selected persona's settings
        if persona in self.config['personas']:
            for key, value in self.config['personas'][persona].items():
                persona_config[key] = value
        
        return persona_config
    
    def get_system_content(self, persona='default') -> str:
        """Get the system content based on the specified persona."""
        persona_config = self._get_persona_config(persona)
        return f"{persona_config['description']}\n" + "\n".join(f"- {trait}" for trait in persona_config['traits'])
    
    def get_model(self, persona='default') -> str:
        """Get the model for the specified persona."""
        return self._get_persona_config(persona)['model']
    
    def get_temperature(self, persona='default') -> float:
        """Get the temperature setting for the specified persona."""
        return self._get_persona_config(persona)['temperature']
    
    def get_voice(self, persona='default') -> str:
        """Get the voice for the specified persona."""
        return self._get_persona_config(persona)['voice']
    
    def get_ollama_url(self) -> str:
        """Get the LMStudio API URL from config."""
        return self.config['url']
    
    def get_headers(self) -> Dict[str, str]:
        """Get the headers from config."""
        return self.config['headers']
    
    def get_persona_choices(self) -> list:
        """Get the list of available personas."""
        return list(self.config['personas'].keys())


# Text Processing
def filter_think_tags(text: str) -> str:
    """Remove text between <think> and </think> tags."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)


# Voice Processing
class VoiceThread:
    """Thread for handling voice output without blocking the main thread."""
    
    def __init__(self, voice, script_dir):
        """Initialize the voice thread."""
        self.voice = voice
        self.script_dir = script_dir
        self.queue = queue.Queue()
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def _run(self):
        """Run the voice thread, processing items from the queue."""
        while self.running:
            try:
                # Get an item from the queue with a timeout
                audio_file = self.queue.get(timeout=0.5)
                if audio_file is None:  # Shutdown signal
                    break
                
                # Play the audio file
                self._play_audio(audio_file)
                
                # Mark the task as done
                self.queue.task_done()
            except queue.Empty:
                # No items in the queue, continue waiting
                continue
            except Exception as e:
                print(f"Error in voice thread: {e}")
    
    def _play_audio(self, audio_file):
        """Play audio from a file."""
        pygame.mixer.init()
        
        try:
            # Load and play the audio
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for the audio to finish playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Clean up
            pygame.mixer.quit()
            # Remove the temporary file
            try:
                os.unlink(audio_file)
            except:
                pass
        except Exception as e:
            print(f"Error playing audio: {e}")
            # Clean up
            pygame.mixer.quit()
            # Remove the temporary file if it exists
            try:
                if os.path.exists(audio_file):
                    os.unlink(audio_file)
            except:
                pass
    
    def add_audio_file(self, audio_file):
        """Add an audio file to the queue for processing."""
        if self.running:
            self.queue.put(audio_file)
    
    def clear_queue(self):
        """Clear all pending audio files from the queue."""
        # Create a new empty queue
        new_queue = queue.Queue()
        
        # Get the old queue
        old_queue = self.queue
        
        # Replace the old queue with the new one
        self.queue = new_queue
        
        # Process any remaining items in the old queue to clean up files
        try:
            while True:
                audio_file = old_queue.get_nowait()
                # Mark as done to avoid blocking
                old_queue.task_done()
                # Clean up the file if it exists
                try:
                    if os.path.exists(audio_file):
                        os.unlink(audio_file)
                except:
                    pass
        except queue.Empty:
            # Queue is empty, nothing to do
            pass
    
    def shutdown(self):
        """Shutdown the voice thread."""
        self.running = False
        self.queue.put(None)  # Signal to stop
        self.thread.join()


async def generate_audio_file(text, voice):
    """Generate an audio file from text and return the path to the file."""
    try:
        # Strip asterisks from text
        text = text.replace('*', '')
        
        # Create a temporary file with .mp3 extension
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Generate and save the audio to the temporary file
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_path)
        
        return temp_path
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None


def stream_response(response, voice=None, script_dir=None):
    """Stream the response from the API and process it sentence by sentence."""
    full_response = ""
    current_sentence = ""
    combined_sentences = ""
    has_choices = False
    
    # Initialize voice thread if voice and script_dir are provided
    voice_thread = None
    if voice and script_dir:
        voice_thread = VoiceThread(voice, script_dir)
    
    try:
        for line in response:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                try:
                    chunk = json.loads(line[6:])
                    if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                        has_choices = True
                        content = chunk['choices'][0]['delta']['content']
                        
                        # Output text character by character
                        for char in content:
                            print(char, end='', flush=True)
                            # Add a small delay for a typing effect
                            time.sleep(0.01)
                        
                        full_response += content
                        current_sentence += content
                        
                        # Check if we have a complete sentence
                        if any(current_sentence.strip().endswith(end) for end in ['.', '!', '?', '...']):
                            # Process the current sentence
                            filtered_sentence = filter_think_tags(current_sentence.strip())
                            
                            # Add the filtered sentence to the combined sentences
                            if filtered_sentence:
                                if combined_sentences:
                                    combined_sentences += " " + filtered_sentence
                                else:
                                    combined_sentences = filtered_sentence
                            
                            # Check if combined sentences are long enough to process
                            if combined_sentences and len(combined_sentences) > 128 and voice_thread:
                                # Generate audio file in the main thread
                                audio_file = asyncio.run(generate_audio_file(combined_sentences, voice))
                                if audio_file:
                                    # Add the audio file to the voice queue
                                    voice_thread.add_audio_file(audio_file)
                                # Reset combined sentences
                                combined_sentences = ""
                            
                            current_sentence = ""
                except json.JSONDecodeError:
                    continue
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Stopping response generation...")
        # Clean up voice thread if it exists
        if voice_thread:
            voice_thread.shutdown()
        raise
    
    # Process any remaining text
    if current_sentence.strip():
        filtered_sentence = filter_think_tags(current_sentence.strip())
        if filtered_sentence:
            if combined_sentences:
                combined_sentences += " " + filtered_sentence
            else:
                combined_sentences = filtered_sentence
    
    # Process any remaining combined sentences
    if combined_sentences and voice_thread:
        # Generate audio file in the main thread
        audio_file = asyncio.run(generate_audio_file(combined_sentences, voice))
        if audio_file:
            # Add the audio file to the voice queue
            voice_thread.add_audio_file(audio_file)
    
    print()  # Add a newline at the end
    
    if not has_choices:
        print("I don't know right now")
        full_response = "I don't know right now"
    
    # Don't wait for voice tasks to complete, just return the response
    # The voice thread will continue running in the background
    return full_response, voice_thread


def call_llm_api(data: dict, url: str, headers: dict) -> Any:
    """Call the LLM API with the given data, URL, and headers, and return the response."""
    # Convert data to JSON string and encode it
    data = json.dumps(data).encode('utf-8')

    # Create request object
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    # Send request and return the response object without reading it
    return urllib.request.urlopen(req)


def get_initial_data_and_response(message: str, config: Config) -> str:
    """Prepare the initial data, get the response, and rewrite the message."""
    # Use the default persona from config
    persona = config.get_persona_choices()[0]

    # Prepare initial data
    initial_data = {
        "model": "hermes-3-llama-3.2-3b",
        "temperature": config.get_temperature(persona),
        "messages": [
            {"role": "system", "content": "Only respond with a single Wikipedia url and nothing else, only respond with plain text do not use markdown or html"},
            {"role": "user", "content": message}
        ],
        "stream": False
    }
    
    # Call the LLM API with the initial data
    initial_response = call_llm_api(initial_data, config.get_ollama_url(), config.get_headers())
    
    # Process the initial response using 'with' syntax
    with initial_response as response:
        url_response = response.read().decode('utf-8')
        
        # Parse the message from the first choice in the response
        response_data = json.loads(url_response)
        if response_data.get('choices') and response_data['choices'][0].get('message', {}).get('content'):
            parsed_message = response_data['choices'][0]['message']['content']
            
            # Use a rigorous URL parser
            parsed_url = urlparse(parsed_message)
            if parsed_url.scheme and parsed_url.netloc:
                extracted_url = parsed_url.geturl()
                print(f"Grabbing context from: {extracted_url} \n\n")
                context = download_and_extract_content(extracted_url)
                now = datetime.now()
                today = now.strftime("%B %d, %Y")
                return f"""
Here is some context for the query:
{context}

Source: {extracted_url} (Last updated {today})

Here is the query:
{message}

Answer the query based on the context and cite your source.
"""
        return message


def process_message(message: str, persona: str, config: Config, conversation_history: list = None, voice: str = None, script_dir: str = None) -> str:
    """Process the message and return the response."""
    if conversation_history is None:
        conversation_history = [
            { "role": "system", "content": config.get_system_content(persona) }
        ]
    
    # Add user's message to conversation history
    conversation_history.append({ "role": "user", "content": message })
    
    data = {
        "model": config.get_model(persona),
        "temperature": config.get_temperature(persona),
        "messages": conversation_history,
        "stream": True
    }
    response = call_llm_api(data, config.get_ollama_url(), config.get_headers())
    try:
        # Use the response with 'with' syntax
        with response as resp:
            # Use the persona's voice if no voice is specified
            if voice is None:
                voice = config.get_voice(persona)
            
            # Stream the response and process it sentence by sentence
            full_response, voice_thread = stream_response(resp, voice, script_dir)
            
            # Add assistant's response to conversation history
            conversation_history.append({ "role": "assistant", "content": full_response })
            
            # Get additional input without going to a new line
            print(">> ", end='', flush=True)
            additional_input = input().strip()
            
            if additional_input:
                # Shutdown the voice thread if it exists
                if voice_thread is not None:
                    voice_thread.shutdown()
                
                # Recursively process the additional input with the updated conversation history
                return process_message(additional_input, persona, config, conversation_history, voice, script_dir)
            
            # Return the filtered response without speaking it again
            return filter_think_tags(full_response)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting conversation...")
        # Ensure pygame is properly cleaned up
        try:
            pygame.mixer.quit()
        except:
            pass
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        # Ensure pygame is properly cleaned up
        try:
            pygame.mixer.quit()
        except:
            pass
        return f"I encountered an error: {str(e)}"


def download_and_extract_content(url: str) -> str:
    """Download an HTML page from a URL and extract the main content, limited to 4048 tokens."""
    try:
        # Send a request to the URL
        with urllib.request.urlopen(url) as response:
            html = response.read()
            
        # Parse the HTML content
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract the main content (e.g., from <main> or <body> tags)
        main_content = soup.find('main') or soup.find('body')
        
        # Get text content
        if main_content:
            text_content = main_content.get_text(separator=' ', strip=True)
            # Remove content within square brackets
            text_content = re.sub(r'\[.*?\]', '', text_content)
            
            # Limit the number of tokens to 1024
            tokens = text_content.split()
            limited_content = ' '.join(tokens[:3024])
            return limited_content
        else:
            return "No main content found."
    except Exception as e:
        return f"Error downloading or parsing content: {e}"


def main():
    """Main entry point for the script."""
    # Initialize configuration first to get persona choices
    config = Config()
    persona_choices = config.get_persona_choices()
    
    parser = argparse.ArgumentParser(description='Process a message and generate a response with text-to-speech.')
    parser.add_argument('message', nargs='*', help='The message to process. If not provided, will read from stdin.')
    parser.add_argument('--voice', help='Edge TTS voice to use (overrides persona default)')
    parser.add_argument('--persona', default='default', 
                       choices=persona_choices, 
                       help='Response persona')
    parser.add_argument('--no-voice', action='store_true', help='Disable voice output')
    args = parser.parse_args()
    
    # Get message from arguments or stdin
    if args.message:
        message = ' '.join(args.message)
 
    if not sys.stdin.isatty():
        message = sys.stdin.read().strip() + "\n" + message
        sys.stdin = open("/dev/tty")
    
    if not message:
        print("Error: No message provided")
        return
    
    # Get the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    
    try:
        # Check if the persona has 'get_pre_context' in main
        persona_config = config._get_persona_config(args.persona)
        if persona_config.get('get_pre_context', False):
            # Prepare initial call to LLM API and rewrite the message
            message = get_initial_data_and_response(message, config)
        
        # Process the message
        process_message(message, args.persona, config, voice=args.voice, script_dir=script_dir)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting gracefully...")
        # Ensure pygame is properly cleaned up
        try:
            pygame.mixer.quit()
        except:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()      