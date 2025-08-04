import pyttsx3

# Initialize the TTS engine
engine = pyttsx3.init()

# Optional: Set properties like voice, rate, and volume
engine.setProperty('rate', 150)     # Speed (default ~200)
engine.setProperty('volume', 1.0)   # Volume (0.0 to 1.0)

# Optional: Choose a different voice (e.g., female)
voices = engine.getProperty('voices')
for idx, voice in enumerate(voices):
    print(f"Voice {idx}: {voice.name} - {voice.id}")
# Choose a voice (e.g., 1 for female, 0 for male)
engine.setProperty('voice', voices[1].id)

# Speak the text
text = "Hello! This is a text to speech demo on macOS."
engine.say(text)

# Wait for speech to finish
engine.runAndWait()