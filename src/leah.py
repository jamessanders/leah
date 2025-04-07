#!/usr/bin/env python3

"""
Leah - A Python script for processing messages and generating text-to-speech responses.
This script interacts with an LMStudio API for message processing and edge-tts for voice synthesis.
"""

import argparse
import asyncio
import edge_tts
import json
import os
import re
import sys
import tempfile
import urllib.request
from typing import Any
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from datetime import datetime
from voice_thread import VoiceThread
from config import Config
from content_extractor import download_and_extract_content
from get_initial_data_and_response import get_initial_data_and_response


# Suppress pygame output
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame


# Text Processing
def filter_think_tags(text: str) -> str:
    """Remove text between <think> and </think> tags."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)


# Voice Processing
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

def process_message(message: str, persona: str, config: Config, conversation_history: list = None, voice: str = None, script_dir: str = None, last_context: str = None) -> str:
   # Check if the persona has 'get_pre_context' in main
    original_message = message
    links_content = ''
    persona_config = config._get_persona_config(persona)
    
    # Check if the message contains a URL
    has_url, extracted_url = check_for_urls(message)
    
    if persona_config.get('get_pre_context', False):
        # If message contains a URL, fetch it directly
        if has_url:
            print(f"Grabbing the requested context from: {extracted_url}")
            limited_content, links, status_code = download_and_extract_content(extracted_url)
            if status_code == 200:
                message = context_template(original_message, limited_content, extracted_url)
            else:
                # If URL fetch fails, use the normal flow
                print("URL fetch failed")
                message = context_template(original_message, 'Failed to fetch context from the provided url', extracted_url)
        # Otherwise use the normal flow
        elif conversation_history is None:
            limited_content, links_content, extracted_url = get_initial_data_and_response(message, config)
            original_message = message
            message = context_template(message, limited_content, extracted_url)
        else:
            if message.startswith('!') and not last_context is None:
                message = message[1:]
                limited_content, links_content, extracted_url = get_initial_data_and_response(context_template(message, last_context, ''), config)
                original_message = message
                message = context_template(message, limited_content, extracted_url)  

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
            
            # Get additional input without going to a new line
            print(">> ", end='', flush=True)
            additional_input = input().strip()
            
            if additional_input:
                # Shutdown the voice thread if it exists
                if voice_thread is not None:
                    voice_thread.shutdown()
                 
                has_url, extracted_url = check_for_urls(additional_input)
                if additional_input.startswith('!') or has_url:
                    conversation_history.pop()
                    conversation_history.append({ "role": "user", "content": original_message })

                # Add assistant's response to conversation history
                conversation_history.append({ "role": "assistant", "content": full_response })

                # Recursively process the additional input with the updated conversation history
                return process_message(additional_input, persona, config, conversation_history, voice, script_dir, links_content)
            
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


def extract_main_content_and_links(html: bytes, base_url: str) -> tuple:
    """Extract the main content and links from HTML content."""
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
        limited_content = ' '.join(tokens[:7000])
        
        # Extract all links with text from the main content and ensure they are fully qualified
        links = [f"<a href='{urljoin(base_url, a['href'])}'>{a.get_text(strip=True)}</a>" for a in main_content.find_all('a', href=True) if a.get_text(strip=True)]
        
        # Limit the number of links to 32
        links = links[:256]
        
        return limited_content, links
    else:
        return "No main content found.", []


def download_and_extract_content(url: str) -> tuple:
    """Download an HTML page from a URL and extract the main content, limited to 4048 tokens, and return the HTTP status code."""
    try:
        # Send a request to the URL
        with urllib.request.urlopen(url) as response:
            html = response.read()
            status_code = response.getcode()
            
        if status_code != 200:
            return None, None, status_code
        
        # Extract main content and links
        limited_content, links = extract_main_content_and_links(html, url)
        
        # Return the limited content and links separately in a tuple
        return limited_content, links, status_code
    except Exception as e:
        return f"Error downloading or parsing content: {e}", None, 404


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