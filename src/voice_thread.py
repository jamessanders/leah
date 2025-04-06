#!/usr/bin/env python3

"""
VoiceThread - A module for handling voice output without blocking the main thread.
"""

import os
import queue
import threading

# Suppress pygame output
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame
import sys

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