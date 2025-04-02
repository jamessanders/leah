#!/usr/bin/env python3

import urllib.request
import json
import sys
import asyncio
import edge_tts
import io
import re
import argparse


async def speak_text(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save("temp.mp3")
    # Use afplay on macOS to play the audio
    import subprocess
    subprocess.run(["afplay", "temp.mp3"])
    # Clean up the temporary file
    import os
    os.remove("temp.mp3")


def filter_think_tags(text):
    # Remove text between <think> and </think> tags
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)


def get_system_content(tone):
    tones = {
        'cheerful': "You are a cheerful and enthusiastic assistant. Be upbeat and positive in your responses. Use casual, friendly language with lots of exclamation marks and positive words! Don't use markdown or emojis, just use plain text.",
        'serious': "You are a serious and professional assistant. Be direct and precise in your responses. Use formal language and avoid casual expressions. Don't use markdown or emojis, just use plain text.",
        'casual': "You are a casual and laid-back assistant. Be conversational and use everyday language. Feel free to use common expressions and contractions. Don't use markdown or emojis, just use plain text.",
        'friendly': "You are a friendly and approachable assistant. Be warm and welcoming in your responses. Use gentle, encouraging language. Don't use markdown or emojis, just use plain text.",
        'irish_female': "You are a friendly Irish female assistant. Be warm and welcoming but concise. Use casual, friendly language with occasional Irish expressions. Keep responses brief and to the point. Don't use markdown or emojis, just use plain text.",
        'default': "You are a helpful assistant that can answer questions and help with tasks. Be concise. Don't use markdown or emojis, just use plain text. Use casual language, don't be stuffy."
    }
    return tones.get(tone.lower(), tones['default'])


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Chat with an AI assistant')
    parser.add_argument('--voice', default='en-US-AvaNeural', help='Edge TTS voice to use (default: en-US-AvaNeural)')
    parser.add_argument('--model', default='hermes-3-llama-3.2-3b', help='Model to use (default: hermes-3-llama-3.2-3b)')
    parser.add_argument('--tone', default='default', help='Tone to use (default, cheerful, serious, casual, friendly, irish_female)')
    parser.add_argument('message', nargs='*', help='Message to send to the AI')
    
    args = parser.parse_args()
    
    # Get message from command line arguments or stdin
    user_message = ' '.join(args.message) if args.message else ""
    
    # Read from stdin if available
    if not sys.stdin.isatty():
        stdin_text = sys.stdin.read().strip()
        if stdin_text:
            user_message = f"{user_message} {stdin_text}".strip() if user_message else stdin_text
    
    if not user_message:
        print("Usage: python leah.py [--voice VOICE] [--model MODEL] [--tone TONE] your message here")
        print("Or pipe text to stdin: echo 'your message' | python leah.py [--voice VOICE] [--model MODEL] [--tone TONE]")
        sys.exit(1)
    
    url = "http://localhost:1234/v1/chat/completions"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "model": args.model,
        "temperature": 1.5,
        "messages": [
            { "role": "system", "content": get_system_content(args.tone) },
            { "role": "user", "content": user_message }
        ],
        "stream": True
    }                                                           

    # Convert data to JSON string and encode it
    data = json.dumps(data).encode('utf-8')
    
    # Create request object
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
        
        # Filter out think tags and speak the complete response
        filtered_response = filter_think_tags(full_response)
        asyncio.run(speak_text(filtered_response, args.voice))

if __name__ == "__main__":
    main()      