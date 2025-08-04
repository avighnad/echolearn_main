import sounddevice as sd
import numpy as np
import speech_recognition as sr
import pyttsx3

# Initialize recognizer and TTS engine
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()

# Configure TTS settings
def configure_tts_engine():
    tts_engine.setProperty('rate', 150)  # Speed
    tts_engine.setProperty('volume', 1.0)  # Volume

    voices = tts_engine.getProperty('voices')
    # Optional: Change voice (0 = male, 1 = female)
    if len(voices) > 1:
        tts_engine.setProperty('voice', voices[1].id)

# Text to Speech function
def speak_text(text):
    print("Speaking:", text)
    tts_engine.say(text)
    tts_engine.runAndWait()

# Record audio from mic
def record_audio(duration=5, samplerate=16000):
    print(f"\n🎙️ Recording for {duration} seconds...")
    audio_data = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()
    print("✅ Recording complete.")
    return np.squeeze(audio_data)

# Convert recorded audio to text
def speech_to_text(audio_array, sample_rate=16000):
    audio = sr.AudioData(audio_array.tobytes(), sample_rate, 2)
    try:
        print("🧠 Recognizing speech...")
        text = recognizer.recognize_google(audio)
        print("📝 You said:", text)
        return text
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
    except sr.RequestError:
        print("⚠️ Could not request results from Google API.")
    return None

# Main flow
if __name__ == "__main__":
    configure_tts_engine()

    # Step 1: Record speech and convert to text
    audio_data = record_audio(duration=5)
    recognized_text = speech_to_text(audio_data)

    # Step 2: Speak the recognized text
    if recognized_text:
        speak_text(recognized_text)
    else:
        speak_text("Sorry, I could not understand what you said.")
