#!/usr/bin/env python3

"""
Leah - A Python script for processing messages and generating text-to-speech responses.
This script interacts with an Ollama API for message processing and edge-tts for voice synthesis.
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
import urllib.request
from typing import Dict, Any

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
        """Load configuration from config.json."""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def get_system_content(self, tone='default') -> str:
        """Get the system content based on the specified tone."""
        tone_config = self.config['tones'].get(tone, self.config['tones']['default'])
        return f"{tone_config['description']}\n" + "\n".join(f"- {trait}" for trait in tone_config['traits'])
    
    def get_ollama_url(self) -> str:
        """Get the Ollama API URL from config."""
        return self.config['url']
    
    def get_headers(self) -> Dict[str, str]:
        """Get the headers from config."""
        return self.config['headers']
    
    def get_temperature(self) -> float:
        """Get the temperature setting from config."""
        return self.config['temperature']


# Text Processing
def filter_think_tags(text: str) -> str:
    """Remove text between <think> and </think> tags."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)


# Message Processing
def process_message(message: str, model: str, tone: str, config: Config) -> str:
    """Process the message and return the response."""
    data = {
        "model": model,
        "temperature": config.get_temperature(),
        "messages": [
            { "role": "system", "content": config.get_system_content(tone) },
            { "role": "user", "content": message }
        ],
        "stream": True
    }
    
    # Convert data to JSON string and encode it
    data = json.dumps(data).encode('utf-8')
    
    # Create request object
    url = config.get_ollama_url()
    headers = config.get_headers()
    
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
        
        return filter_think_tags(full_response)


# Audio Generation
async def speak_text(text: str, voice: str, script_dir: str) -> None:
    """Generate and play audio from text using a temporary file."""
    pygame.mixer.init()
    
    try:
        # Create a temporary file with .mp3 extension
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Generate and save the audio to the temporary file
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_path)
        
        # Load and play the audio
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        
        # Wait for the audio to finish playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    finally:
        # Clean up
        pygame.mixer.quit()
        # Remove the temporary file
        try:
            os.unlink(temp_path)
        except:
            pass


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Process a message and generate a response with text-to-speech.')
    parser.add_argument('message', nargs='*', help='The message to process. If not provided, will read from stdin.')
    parser.add_argument('--voice', default='en-US-AvaNeural', help='Edge TTS voice to use')
    parser.add_argument('--model', default='gemma-3-27b-it', help='AI model to use')
    parser.add_argument('--tone', default='default', 
                       choices=['default', 'cheerful', 'serious', 'casual', 'friendly'], 
                       help='Response tone')
    parser.add_argument('--no-voice', action='store_true', help='Disable voice output')
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
    
    # Initialize configuration
    config = Config()
    
    # Process the message
    response = process_message(message, args.model, args.tone, config)
    
    # Generate and play audio if voice is enabled
    if not args.no_voice:
        asyncio.run(speak_text(response, args.voice, script_dir))


if __name__ == "__main__":
    main()      