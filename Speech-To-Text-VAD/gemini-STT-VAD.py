
import os
import time
import wave
import numpy as np
import google.generativeai as genai
import pyaudio
import threading
from queue import Queue
import base64
import io
from dotenv import load_dotenv

# --- New Imports for VAD ---
import webrtcvad
from collections import deque
# ---------------------------

# Load environment variables from .env file
load_dotenv()

# ANSI color codes for terminal output
NEON_GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET_COLOR = "\033[0m"

# Configure Google Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    print(f"{RED}Error: GOOGLE_API_KEY not found. Please check your .env file.{RESET_COLOR}")
    exit(1)
genai.configure(api_key=GOOGLE_API_KEY)

# Configuration
TARGET_LANGUAGE = "English"  # Change to desired target language
SOURCE_LANGUAGE = "auto"  # Auto-detect source language
OUTPUT_FILE = "translation_output.txt"

# --- VAD & Audio parameters ---
# VAD works with 16-bit mono PCM audio.
# We'll use 16kHz sample rate, which is good for speech.
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Sample rate in Hz (16kHz is required by some VADs)

# VAD works with specific frame durations: 10, 20, or 30 ms.
# We'll use 30ms frames.
VAD_FRAME_DURATION_MS = 30
VAD_SAMPLES_PER_FRAME = int(RATE * VAD_FRAME_DURATION_MS / 1000)
VAD_CHUNK_SIZE_BYTES = VAD_SAMPLES_PER_FRAME * 2  # 2 bytes for paInt16

# We'll use a ring buffer to hold a small amount of audio *before* speech starts.
# This helps catch the very beginning of a word.
# 10 frames * 30ms = 300ms of audio buffer
SILENCE_PADDING_FRAMES = 10

# We'll wait this long after speech stops before sending the chunk.
# 50 frames * 30ms = 1.5 seconds of silence
SILENCE_TIMEOUT_FRAMES = 50
# ------------------------------

# Queue for passing audio chunks between threads
audio_queue = Queue()
should_stop = threading.Event()

def save_audio_as_wav(frames, filename):
    """Save audio frames as a WAV file."""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 2 bytes for paInt16
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    return True

def get_input_devices():
    """List all available input devices."""
    p = pyaudio.PyAudio()
    info = "\nAvailable input devices:\n"
    
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:  # Only input devices
            info += f"Device {i}: {dev_info.get('name')}\n"
    
    p.terminate()
    return info

def translate_chunk(model_name, chunk_file):
    """Translate audio using Google Gemini."""
    try:
        # Verify file exists and has content
        if not os.path.exists(chunk_file) or os.path.getsize(chunk_file) < 100:
            print(f"{RED}Warning: Audio file empty or too small{RESET_COLOR}")
            return ""

        # Read the audio file
        with open(chunk_file, 'rb') as f:
            file_content = f.read()
        
        # Create Gemini model
        google_model = genai.GenerativeModel(model_name=model_name)

        # Use a more direct prompt focused on transcription first
        transcription_prompt = f"""
        Transcribe the speech in this audio file. 
        Only return the transcribed text without any additional information or explanations.
        If there is no speech detected, return exactly "NO_SPEECH_DETECTED".
        """

        # Generate content with Gemini
        response = google_model.generate_content(
            contents=[
                {'text': transcription_prompt},
                {'inline_data': {'mime_type': 'audio/wav', 'data': file_content}}
            ]
        )

        # Get the transcription
        transcription = response.text.strip()
        
        # Check if no speech was detected
        if transcription == "NO_SPEECH_DETECTED" or not transcription:
            return ""
            
        # If source language is not English and target is English, we need to translate
        if SOURCE_LANGUAGE != "auto" and SOURCE_LANGUAGE.lower() != "english" and TARGET_LANGUAGE.lower() == "english":
            translation_prompt = f"Translate this from {SOURCE_LANGUAGE} to {TARGET_LANGUAGE}: {transcription}"
            translation_response = google_model.generate_content(translation_prompt)
            return translation_response.text.strip()
        
        # Otherwise just return the transcription
        return transcription
        
    except Exception as e:
        print(f"{RED}Error translating chunk: {str(e)}{RESET_COLOR}")
        time.sleep(1)  # Wait a bit if there was an error
        return ""

def record_audio(device_index=None):
    """
    Thread function to continuously record audio and use VAD
    to detect speech and silence.
    """
    p = pyaudio.PyAudio()
    
    # --- VAD Setup ---
    vad = webrtcvad.Vad()
    # Set VAD aggressiveness (0-3, 3 is most aggressive)
    vad.set_mode(3)
    
    ring_buffer = deque(maxlen=SILENCE_PADDING_FRAMES)
    voiced_frames = []
    is_speaking = False
    frames_since_speech = 0
    # -----------------
    
    try:
        # Open audio stream
        kwargs = {
            'format': FORMAT,
            'channels': CHANNELS,
            'rate': RATE,
            'input': True,
            'frames_per_buffer': VAD_SAMPLES_PER_FRAME  # Use VAD frame size
        }
        
        # Add device index if specified
        if device_index is not None:
            kwargs['input_device_index'] = device_index
            
        stream = p.open(**kwargs)
        
        print(f"{BLUE}Recording started. Press Ctrl+C to stop.{RESET_COLOR}")
        print(f"{BLUE}Listening for speech...{RESET_COLOR}")
        
        while not should_stop.is_set():
            # Read one VAD-sized frame
            frame = stream.read(VAD_SAMPLES_PER_FRAME, exception_on_overflow=False)
            
            # Check if frame contains speech
            try:
                is_speech = vad.is_speech(frame, RATE)
            except Exception as e:
                print(f"{RED}VAD error: {e}{RESET_COLOR}")
                continue

            if is_speech:
                if not is_speaking:
                    # Speech started
                    print(f"{BLUE}Speech detected...{RESET_COLOR}")
                    is_speaking = True
                    # Add the padding frames from before speech started
                    voiced_frames.extend(list(ring_buffer))
                
                voiced_frames.append(frame)
                frames_since_speech = 0
            
            elif not is_speech and is_speaking:
                # Speech has (perhaps temporarily) stopped
                frames_since_speech += 1
                voiced_frames.append(frame) # Add silence padding
                
                if frames_since_speech > SILENCE_TIMEOUT_FRAMES:
                    # Silence timeout reached, end of utterance
                    print(f"{BLUE}Speech ended. Processing chunk...{RESET_COLOR}")
                    is_speaking = False
                    frames_since_speech = 0
                    
                    # Send the complete speech chunk to the processing thread
                    audio_queue.put(voiced_frames.copy())
                    
                    # Clear buffers
                    voiced_frames = []
                    ring_buffer.clear()
            
            elif not is_speech and not is_speaking:
                # We are in a silent period
                # Just keep the ring buffer full of recent silence
                ring_buffer.append(frame)

    except Exception as e:
        print(f"{RED}Error in recording: {str(e)}{RESET_COLOR}")
    
    finally:
        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        p.terminate()
        print(f"{BLUE}Recording stopped.{RESET_COLOR}")

def process_audio():
    """Thread function to process recorded audio chunks."""
    accumulated_transcription = ""
    chunk_file = "temp_chunk.wav"
    chunk_counter = 0
    
    try:
        while not should_stop.is_set() or not audio_queue.empty():
            if not audio_queue.empty():
                frames = audio_queue.get()
                chunk_counter += 1
                
                # Save the chunk as a temporary WAV file
                save_audio_as_wav(frames, chunk_file)
                
                print(f"{BLUE}Processing chunk {chunk_counter}...{RESET_COLOR}")
                
                # Translate the chunk
                translation = translate_chunk('gemini-2.5-flash', chunk_file)
                
                # Print the translation with color if not empty
                if translation and translation.strip():
                    # Print in neon green
                    print(f"{NEON_GREEN}{translation}{RESET_COLOR}", end=" ", flush=True)
                    
                    # Append the new translation to the accumulated transcription
                    accumulated_transcription += translation + " "
                else:
                    print(f"{RED}[No speech detected in chunk {chunk_counter}]{RESET_COLOR}")
                
                # Remove the temporary file
                try:
                    os.remove(chunk_file)
                except:
                    pass
            else:
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
    
    except Exception as e:
        print(f"{RED}Error in processing: {str(e)}{RESET_COLOR}")
    
    finally:
        # Write the accumulated transcription to the log file
        print(f"\n{BLUE}--- End of Session ---{RESET_COLOR}")
        print(f"Full transcription:\n{accumulated_transcription}")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(accumulated_transcription)
        print(f"{BLUE}Full transcription saved to {OUTPUT_FILE}{RESET_COLOR}")

def main():
    """Main function to handle the recording and processing."""
    try:
        # Ask for device index
        print(get_input_devices())
        device_input = input("Enter input device number (leave blank for default): ").strip()
        device_index = int(device_input) if device_input else None
        
        # Start recording thread
        record_thread = threading.Thread(target=record_audio, args=(device_index,))
        record_thread.start()
        
        # Start processing thread
        process_thread = threading.Thread(target=process_audio)
        process_thread.start()
        
        # Wait for keyboard interrupt
        while True:
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nStopping...")
        should_stop.set()
        
        # Wait for threads to finish
        record_thread.join()
        process_thread.join()

if __name__ == "__main__":
    main()