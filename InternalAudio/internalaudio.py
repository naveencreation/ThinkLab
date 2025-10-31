#Internal audio Recording only


import pyaudiowpatch as pyaudio
import time
import wave
import sys

# --- Configuration ---
RECORD_SECONDS = 10.0  # Duration of the recording
OUTPUT_FILENAME = "system_audio.wav"  # File to save the recording to
CHUNK_SIZE = 512      # Number of frames per buffer
# ---------------------

def record_system_audio():
    """
    Records system audio using PyAudioWPatch and saves it to a WAV file.
    """
    print(f"Recording {RECORD_SECONDS} seconds of system audio to {OUTPUT_FILENAME}...")

    # Use context managers for automatic resource cleanup
    with pyaudio.PyAudio() as p:
        try:
            # Get default WASAPI info
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("Looks like WASAPI is not available on the system. Exiting...")
            sys.exit(-1)
        
        # Get default WASAPI speakers (output device)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        # Check if the default speakers are already a loopback device
        if not default_speakers["isLoopbackDevice"]:
            print("Default speakers not a loopback device. Searching for a match...")
            found_loopback = False
            # Iterate over all loopback devices
            for loopback in p.get_loopback_device_info_generator():
                """
                Try to find loopback device with same name(and [Loopback suffix]).
                Unfortunately, this is the most adequate way at the moment.
                """
                # Check if the default speaker's name is part of the loopback device's name
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    found_loopback = True
                    print(f"Found loopback device: {default_speakers['name']}")
                    break
            
            if not found_loopback:
                print("\nCould not find a loopback device for the default speakers.")
                print("Please run `python -m pyaudiowpatch` to see available devices.")
                print("Exiting...")
                sys.exit(-1)
        else:
             print(f"Using default loopback device: {default_speakers['name']}")
                   
        print(f"\nRecording from: ({default_speakers['index']}) {default_speakers['name']}\n")
        
        # --- Setup the .wav file ---
        #
        wave_file = wave.open(OUTPUT_FILENAME, 'wb')
        wave_file.setnchannels(default_speakers["maxInputChannels"]) #
        wave_file.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16)) #
        wave_file.setframerate(int(default_speakers["defaultSampleRate"])) #
        # --------------------------

        # --- Define the audio stream callback ---
        def callback(in_data, frame_count, time_info, status):
            """This function is called by PyAudio for each chunk of audio."""
            # Write the audio data to the wave file
            wave_file.writeframes(in_data) #
            # Tell PyAudio to continue recording
            return (in_data, pyaudio.paContinue) #
        # --------------------------------------

        # --- Open the audio stream ---
        # We use another context manager to auto-close the stream
        #
        try:
            with p.open(format=pyaudio.paInt16,
                    channels=default_speakers["maxInputChannels"],
                    rate=int(default_speakers["defaultSampleRate"]),
                    frames_per_buffer=CHUNK_SIZE,
                    input=True,
                    input_device_index=default_speakers["index"],
                    stream_callback=callback
            ) as stream:
                
                print(f"Recording... Press Ctrl+C to stop early.")
                # Wait for the recording to finish
                # The actual recording happens in the 'callback' function
                time.sleep(RECORD_SECONDS) #
                
        except KeyboardInterrupt:
            print("Recording stopped early by user.")
        except Exception as e:
            print(f"An error occurred during recording: {e}")
        # -----------------------------

        # --- Cleanup ---
        print("Recording finished.")
        wave_file.close() #
        # The stream and PyAudio instance are closed automatically
        # by their 'with' statements.
        # ----------------

if __name__ == "__main__":
    record_system_audio()



