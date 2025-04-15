from asyncio import sleep
import sounddevice as sd
import numpy as np
import whisper
import argparse
import requests
import json
import os
import pygame
import tempfile
import threading
import queue
import getpass

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Audio to Whisper Transcription')
parser.add_argument('--list', action='store_true', help='List audio devices')
parser.add_argument('--device', type=int, help='Select audio device by number')
parser.add_argument('--login', action='store_true', help='Login to the server')
parser.add_argument('--username', type=str, help='Username for login')
args = parser.parse_args()

host = "http://192.168.196.16:8001"
personas = ["beth", "leah", "ellie"]

if args.list:
    print("Available audio devices:")
    print(sd.query_devices())
    exit(0)

# Initialize Whisper model
model = whisper.load_model("base")

# Audio recording parameters
RATE = 16000
CHANNELS = 1

# Buffer to store audio data
buffer = np.empty((0, CHANNELS))

# Calculate the number of frames for 3 seconds
frames_per_second = RATE


text_buffer = ""

# Queue to hold audio filenames
audio_queue = queue.Queue()

# Initialize pygame mixer at the start of the program
pygame.mixer.init()

# Global variables to store token and username
global_token = None
global_username = None

if args.login:
    if not args.username:
        print("Username is required for login.")
        exit(1)
    # Prompt for password
    password = getpass.getpass(prompt='Password: ')
    # Make a POST request to /login
    response = requests.post(f'{host}/login', json={'username': args.username, 'password': password})
    if response.status_code == 200:
        data = response.json()
        global_token = data.get('token')
        global_username = args.username
        print("Login successful.")
    else:
        print("Login failed.")
        exit(1)

print("Recording...")

# Function to watch the queue and play audio from URLs
def audio_player():
    while True:
        try:
            audio_url = audio_queue.get()
            if audio_url is None:  # Exit signal
                continue
            print(f"Playing audio from {audio_url}")
            # Stream audio from the URL
            with requests.get(audio_url, stream=True) as audio_response:
                with tempfile.NamedTemporaryFile(delete=False) as temp_audio_file:
                    for chunk in audio_response.iter_content(chunk_size=1024):
                        if chunk:
                            temp_audio_file.write(chunk)
                    temp_audio_file_path = temp_audio_file.name
            # Load and play the audio file
            pygame.mixer.music.load(temp_audio_file_path)
            pygame.mixer.music.play()
            # Wait for the music to finish playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            # Clean up the temporary file
            os.remove(temp_audio_file_path)
        except Exception as e:
            print(f"Error playing audio: {e}")
            continue

def send_transcription(text):
    global text_buffer

    if text.strip() == "":
        return False
    
    if text.strip().lower().startswith("stop"):
        stop_audio_playback()
        return False

    text_buffer = " ".join([text_buffer, text.strip()])
    print("Processing transcription:", text_buffer)
    text_buffer = text_buffer.strip()

    watch_word = "nonewatchword"
    for persona in personas:
        if text_buffer.lower().startswith(persona):
            watch_word = persona
            break

    if text_buffer == "" or not text_buffer.lower().startswith(watch_word):
        text_buffer = ""
        return False
    
    if (len(text_buffer[len(watch_word):].strip()) < 3):
        print("Waiting for more input")
        pygame.mixer.music.load("ping.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        return True
    
    final_text = text_buffer
    text_buffer = ""

    stop_audio_playback()

    headers = {
        'Authorization': f'Bearer {global_token}',
        'X-Username': global_username
    }
    print(headers)
    print("Making request")
    with requests.post(f'{host}/query', json={'query': final_text, 'persona': watch_word}, headers=headers, stream=True) as response:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    try:
                        data_json = json.loads(decoded_line[6:])
                        filename = data_json.get('filename')
                        if filename:
                            print(f"Queueing {filename} for playback")
                            # Stream audio from the server
                            audio_url = f"{host}/voice/{filename}"
                            # Add the URL to the queue
                            audio_queue.put(audio_url)
                        elif data_json.get('content',''):
                            print(data_json.get('content'), end="")
                    except json.JSONDecodeError:
                        print("Failed to decode JSON from response.")
    print("Done")

def stop_audio_playback():
    # Stop the current audio playback
    pygame.mixer.music.stop()
    # Clear the audio queue
    while not audio_queue.empty():
        audio_queue.get()
    print("Audio playback stopped and queue cleared.")


try:
    def callback(indata, frames, time, status):
        global buffer
        # Append new data to the buffer
        wait_time = frames_per_second * 2 
        buffer = np.append(buffer, indata, axis=0)
        # Check if buffer has at least 3 seconds of audio
        if len(buffer) >= wait_time:
            # Convert audio data to the format expected by Whisper
            data = buffer[:wait_time, 0]
            # Convert audio data to float32
            data = data.astype(np.float32)
            # Check if there is data to transcribe
            
            # Process audio data with Whisper
            result = model.transcribe(data, language='en')
            wait_more = send_transcription(result['text'])
            # Remove processed data from the buffer
            buffer = buffer[wait_time:]
            if wait_more:
                print("Waiting for 6 seconds")
                waiting_for_silence = True
                wait_time = frames_per_second * 6
            else:
                wait_time = frames_per_second * 3 
              

    # Check if device argument is provided
    if args.device is not None:
        device = args.device
    else:
        device = None  # Use default device

    # Start the audio player thread
    player_thread = threading.Thread(target=audio_player, daemon=True)
    player_thread.start()

    # Start the audio stream with the selected device
    with sd.InputStream(samplerate=RATE, channels=CHANNELS, callback=callback, device=device):
        sd.sleep(1000000)  # Keep the stream open

except KeyboardInterrupt:
    print("Recording stopped by user.")
    # Signal the audio player thread to exit
    audio_queue.put(None)
    player_thread.join()
    print("Audio player thread terminated.")
    exit(0)

except KeyboardInterrupt:
    print("Recording stopped.") 