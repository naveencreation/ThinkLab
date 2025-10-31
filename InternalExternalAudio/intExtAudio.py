#Both internal and mic audio recording
import pyaudiowpatch as pyaudio
import time
import wave
import sys

# --- Configuration ---
RECORD_SECONDS = 15.0  # Duration of the recording
SYSTEM_AUDIO_FILENAME = "system_audio.wav"  # File for system audio
MIC_AUDIO_FILENAME = "mic_audio.wav"        # File for microphone audio
CHUNK_SIZE = 512
# ---------------------

# --- Wave file setup ---
# We need to set up two separate wave files
wave_file_system = wave.open(SYSTEM_AUDIO_FILENAME, 'wb')
wave_file_mic = wave.open(MIC_AUDIO_FILENAME, 'wb')

# --- Stream Callbacks ---
# We also need two separate callback functions, one for each stream

def speaker_callback(in_data, frame_count, time_info, status):
    """Callback for the system audio stream."""
    wave_file_system.writeframes(in_data) #
    return (in_data, pyaudio.paContinue) #

def mic_callback(in_data, frame_count, time_info, status):
    """Callback for the microphone audio stream."""
    wave_file_mic.writeframes(in_data)
    return (in_data, pyaudio.paContinue)

# --------------------------

def record_audio():
    """
    Records both system audio and microphone audio to separate WAV files.
    """
    print(f"Recording {RECORD_SECONDS} seconds...")
    print(f"System audio will be saved to: {SYSTEM_AUDIO_FILENAME}")
    print(f"Microphone audio will be saved to: {MIC_AUDIO_FILENAME}\n")

    # Use context manager for PyAudio
    with pyaudio.PyAudio() as p:
        try:
            # Get default WASAPI info
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("Looks like WASAPI is not available on the system. Exiting...")
            sys.exit(-1)
        
        # --- 1. Find System Audio (Speaker) Device ---
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"]) #
        
        if not default_speakers["isLoopbackDevice"]:
            found_loopback = False
            for loopback in p.get_loopback_device_info_generator(): #
                if default_speakers["name"] in loopback["name"]: #
                    speaker_device_info = loopback #
                    found_loopback = True
                    break
            if not found_loopback:
                print("Could not find a loopback device. Exiting...")
                sys.exit(-1)
        else:
            speaker_device_info = default_speakers

        print(f"Recording System Audio from: ({speaker_device_info['index']}) {speaker_device_info['name']}")

        # --- 2. Find Microphone Device ---
        default_mic_index = wasapi_info.get("defaultInputDevice")
        if default_mic_index is None:
            print("Could not find default WASAPI input device (microphone). Exiting...")
            sys.exit(-1)
            
        mic_device_info = p.get_device_info_by_index(default_mic_index)
        print(f"Recording Microphone from:   ({mic_device_info['index']}) {mic_device_info['name']}\n")

        # --- 3. Configure Wave Files ---
        # Configure system audio wave file
        wave_file_system.setnchannels(speaker_device_info["maxInputChannels"]) #
        wave_file_system.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16)) #
        wave_file_system.setframerate(int(speaker_device_info["defaultSampleRate"])) #
        
        # Configure microphone wave file
        wave_file_mic.setnchannels(mic_device_info["maxInputChannels"])
        wave_file_mic.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
        wave_file_mic.setframerate(int(mic_device_info["defaultSampleRate"]))
        
        # --- 4. Open Streams (Nested) ---
        # We nest the context managers to open both streams
        try:
            # Open system audio stream
            with p.open(format=pyaudio.paInt16,
                    channels=speaker_device_info["maxInputChannels"],
                    rate=int(speaker_device_info["defaultSampleRate"]),
                    frames_per_buffer=CHUNK_SIZE,
                    input=True,
                    input_device_index=speaker_device_info["index"],
                    stream_callback=speaker_callback
            ) as stream_system: #

                # Open microphone stream
                with p.open(format=pyaudio.paInt16,
                        channels=mic_device_info["maxInputChannels"],
                        rate=int(mic_device_info["defaultSampleRate"]),
                        frames_per_buffer=CHUNK_SIZE,
                        input=True,
                        input_device_index=mic_device_info["index"],
                        stream_callback=mic_callback
                ) as stream_mic:
                    
                    print(f"Recording... Press Ctrl+C to stop early.")
                    # Keep the streams alive for the specified duration
                    time.sleep(RECORD_SECONDS) #

        except KeyboardInterrupt:
            print("Recording stopped early by user.")
        except Exception as e:
            print(f"An error occurred during recording: {e}")
        
        finally:
            # --- 5. Cleanup ---
            print("Recording finished.")
            # Close the wave files
            wave_file_system.close() #
            wave_file_mic.close()
            # Streams and PyAudio instance are closed automatically
            # by their 'with' statements.

if __name__ == "__main__":
    record_audio()

