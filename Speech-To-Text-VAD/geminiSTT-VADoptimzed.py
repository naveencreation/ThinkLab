
import os
import time
import wave
import numpy as np
import google.generativeai as genai
import pyaudio
import threading
from queue import Queue
import base64
import io  # <-- Import 'io' for in-memory bytes buffer
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
TARGET_LANGUAGE = "English"
SOURCE_LANGUAGE = "auto"
OUTPUT_FILE = "translation_output.txt"

# --- VAD & Audio parameters ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
VAD_FRAME_DURATION_MS = 30
VAD_SAMPLES_PER_FRAME = int(RATE * VAD_FRAME_DURATION_MS / 1000)
VAD_CHUNK_SIZE_BYTES = VAD_SAMPLES_PER_FRAME * 2
SILENCE_PADDING_FRAMES = 10

# --- SPEED TUNING ---
# This is the silence duration (in frames) after speech before
# processing. 50 frames * 30ms = 1.5 seconds.
# Lower this to ~30 (0.9s) for a faster, more "responsive" feel,
# but you risk cutting off if you pause for too long mid-sentence.
SILENCE_TIMEOUT_FRAMES = 50
# --------------------

# Queue for passing audio chunks between threads
audio_queue = Queue()
should_stop = threading.Event()

def create_wav_in_memory(frames):
    """Saves audio frames as a WAV file *in memory*."""
    # Create an in-memory bytes buffer
    buffer = io.BytesIO()
    
    # Use wave to write PCM data to the buffer
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 2 bytes for paInt16
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    # Get the bytes value from the buffer
    return buffer.getvalue()

def get_input_devices():
    """List all available input devices."""
    p = pyaudio.PyAudio()
    info = "\nAvailable input devices:\n"
    
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:
            info += f"Device {i}: {dev_info.get('name')}\n"
    
    p.terminate()
    return info

def translate_chunk(model_name, wav_bytes): # <-- Accepts bytes, not a filename
    """Translate audio using Google Gemini."""
    try:
        # Verify bytes exist
        if not wav_bytes or len(wav_bytes) < 100:
            print(f"{RED}Warning: Audio data empty or too small{RESET_COLOR}")
            return ""

        # We already have the bytes, no need to read a file
        file_content = wav_bytes
        
        # Create Gemini model
        google_model = genai.GenerativeModel(model_name=model_name)

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

        transcription = response.text.strip()
        
        if transcription == "NO_SPEECH_DETECTED" or not transcription:
            return ""
            
        if SOURCE_LANGUAGE != "auto" and SOURCE_LANGUAGE.lower() != "english" and TARGET_LANGUAGE.lower() == "english":
            translation_prompt = f"Translate this from {SOURCE_LANGUAGE} to {TARGET_LANGUAGE}: {transcription}"
            translation_response = google_model.generate_content(translation_prompt)
            return translation_response.text.strip()
        
        return transcription
        
    except Exception as e:
        print(f"{RED}Error translating chunk: {str(e)}{RESET_COLOR}")
        time.sleep(1)
        return ""

def record_audio(device_index=None):
    """
    Thread function to continuously record audio and use VAD
    to detect speech and silence.
    """
    p = pyaudio.PyAudio()
    
    vad = webrtcvad.Vad()
    vad.set_mode(3)
    
    ring_buffer = deque(maxlen=SILENCE_PADDING_FRAMES)
    voiced_frames = []
    is_speaking = False
    frames_since_speech = 0
    
    try:
        kwargs = {
            'format': FORMAT,
            'channels': CHANNELS,
            'rate': RATE,
            'input': True,
            'frames_per_buffer': VAD_SAMPLES_PER_FRAME
        }
        
        if device_index is not None:
            kwargs['input_device_index'] = device_index
            
        stream = p.open(**kwargs)
        
        print(f"{BLUE}Recording started. Press Ctrl+C to stop.{RESET_COLOR}")
        print(f"{BLUE}Listening for speech...{RESET_COLOR}")
        
        while not should_stop.is_set():
            frame = stream.read(VAD_SAMPLES_PER_FRAME, exception_on_overflow=False)
            
            try:
                is_speech = vad.is_speech(frame, RATE)
            except Exception as e:
                print(f"{RED}VAD error: {e}{RESET_COLOR}")
                continue

            if is_speech:
                if not is_speaking:
                    print(f"{BLUE}Speech detected...{RESET_COLOR}")
                    is_speaking = True
                    voiced_frames.extend(list(ring_buffer))
                
                voiced_frames.append(frame)
                frames_since_speech = 0
            
            elif not is_speech and is_speaking:
                frames_since_speech += 1
                voiced_frames.append(frame)
                
                if frames_since_speech > SILENCE_TIMEOUT_FRAMES:
                    print(f"{BLUE}Speech ended. Processing chunk...{RESET_COLOR}")
                    is_speaking = False
                    frames_since_speech = 0
                    
                    audio_queue.put(voiced_frames.copy())
                    
                    voiced_frames = []
                    ring_buffer.clear()
            
            elif not is_speech and not is_speaking:
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
    chunk_counter = 0
    
    try:
        while not should_stop.is_set() or not audio_queue.empty():
            if not audio_queue.empty():
                frames = audio_queue.get()
                chunk_counter += 1
                
                # --- FASTER ---
                # Create WAV file in memory instead of on disk
                wav_bytes = create_wav_in_memory(frames)
                
                print(f"{BLUE}Processing chunk {chunk_counter}...{RESET_COLOR}")
                
                # Use 'gemini-1.5-flash-latest' for the fastest, most recent model
                translation = translate_chunk('gemini-2.5-flash', wav_bytes)
                # --- END FASTER ---
                
                if translation and translation.strip():
                    print(f"{NEON_GREEN}{translation}{RESET_COLOR}", end=" ", flush=True)
                    accumulated_transcription += translation + " "
                else:
                    print(f"{RED}[No speech detected in chunk {chunk_counter}]{RESET_COLOR}")
                
                # No need to remove a file anymore
            else:
                time.sleep(0.1)
    
    except Exception as e:
        print(f"{RED}Error in processing: {str(e)}{RESET_COLOR}")
    
    finally:
        print(f"\n{BLUE}--- End of Session ---{RESET_COLOR}")
        print(f"Full transcription:\n{accumulated_transcription}")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(accumulated_transcription)
        print(f"{BLUE}Full transcription saved to {OUTPUT_FILE}{RESET_COLOR}")

def main():
    """Main function to handle the recording and processing."""
    try:
        print(get_input_devices())
        device_input = input("Enter input device number (leave blank for default): ").strip()
        device_index = int(device_input) if device_input else None
        
        record_thread = threading.Thread(target=record_audio, args=(device_index,))
        record_thread.start()
        
        process_thread = threading.Thread(target=process_audio)
        process_thread.start()
        
        while True:
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nStopping...")
        should_stop.set()
        
        record_thread.join()
        process_thread.join()

if __name__ == "__main__":
    main()