#!/usr/bin/env python3

import urllib.request
import json
import sys
import asyncio
import edge_tts
import io
import re
import argparse
import os
import textwrap
from typing import Dict, Any
import subprocess


def filter_think_tags(text):
    """Remove text between <think> and </think> tags."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)


async def speak_text(text, voice):
    """Generate and play audio from text."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save("temp.mp3")
    # Use afplay on macOS to play the audio
    subprocess.run(["afplay", "temp.mp3"])
    # Clean up the temporary file
    os.remove("temp.mp3")


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)


def get_system_content(tone='default') -> str:
    """Get the system content based on the specified tone."""
    config = load_config()
    tone_config = config['tones'].get(tone, config['tones']['default'])
    return f"{tone_config['description']}\n" + "\n".join(f"- {trait}" for trait in tone_config['traits'])


def get_ollama_url() -> str:
    """Get the Ollama API URL from config."""
    return load_config()['url']


def get_headers() -> Dict[str, str]:
    """Get the headers from config."""
    return load_config()['headers']


def get_temperature() -> float:
    """Get the temperature setting from config."""
    return load_config()['temperature']


def process_message(message: str, model: str, tone: str) -> str:
    """Process the message and return the response."""
    data = {
        "model": model,
        "temperature": get_temperature(),
        "messages": [
            { "role": "system", "content": get_system_content(tone) },
            { "role": "user", "content": message }
        ],
        "stream": True
    }
    
    # Convert data to JSON string and encode it
    data = json.dumps(data).encode('utf-8')
    
    # Create request object
    url = get_ollama_url()
    headers = get_headers()
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    # Send request and get response
    with urllib.request.urlopen(req) as response:
        full_response = ""
        has_choices = False
        for line in response:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                try:
                    chunk = json.loads(line[6:])
                    if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                        has_choices = True
                        content = chunk['choices'][0]['delta']['content']
                        print(content, end='', flush=True)
                        full_response += content
                except json.JSONDecodeError:
                    continue
        
        print()  # Add a newline at the end
        
        if not has_choices:
            print("I don't know right now")
            full_response = "I don't know right now"
        
        # Filter out think tags and return the complete response
        return filter_think_tags(full_response)


async def generate_audio(text: str, voice: str, script_dir: str) -> None:
    """Generate and play audio from text."""
    # Create a temporary file path in the script's directory
    temp_file = os.path.join(script_dir, "temp.mp3")
    
    # Generate audio using edge-tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(temp_file)
    
    # Play the audio file
    subprocess.run(["afplay", temp_file])
    
    # Clean up the temporary file
    os.remove(temp_file)


def main():
    parser = argparse.ArgumentParser(description='Process a message and generate a response with text-to-speech.')
    parser.add_argument('message', nargs='*', help='The message to process. If not provided, will read from stdin.')
    parser.add_argument('--voice', default='en-US-AvaNeural', help='Edge TTS voice to use')
    parser.add_argument('--model', default='gemma-3-27b-it', help='AI model to use')
    parser.add_argument('--tone', default='default', choices=['default', 'cheerful', 'serious', 'casual', 'friendly'], help='Response tone')
    args = parser.parse_args()
    
    # Get message from arguments or stdin
    if args.message:
        message = ' '.join(args.message)
    else:
        message = sys.stdin.read().strip()
    
    if not message:
        print("Error: No message provided")
        return
    
    # Get the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get configuration
    config = load_config()
    
    # Process the message
    response = process_message(message, args.model, args.tone)
    
    
    # Generate and play audio
    asyncio.run(generate_audio(response, args.voice, script_dir))


if __name__ == "__main__":
    main()      