import speech_recognition as sr
import pyttsx3
import webbrowser
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import time
from gtts import gTTS
from playsound import playsound
import pyowm
from transformers import pipeline
import re
import spacy

engine = pyttsx3.init()
id = "06ea3a05730242f2a62a74e60bd7f886"
secret = "84dbe041c38346a2bce0697648ea8729"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=id,
    client_secret=secret,
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-modify-playback-state,user-read-playback-state"
))

# Initialize zero-shot-classification pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
nlp = spacy.load("en_core_web_sm")


def site_to_open(command):
    words = command.split()

    if "open" in words:
        idx = words.index("open")
        if idx + 1 < len(words):
            next_word = words[idx + 1]
            return next_word
        else:
            print("No word found after 'open'")
    else:
        print("'open' not found in sentence")
        
def get_spotify_device_id():
    """Fetches the ID of the first available Spotify device."""
    devices = sp.devices()
    if devices['devices']:
        # Return the ID of the first device in the list
        return devices['devices'][0]['id']
    else:
        # No active device found
        return None

def get_weather(command):
    owm = pyowm.OWM('fc636c21b823f716d3c3e3a39d1341f6')
    mgr = owm.weather_manager()

    # Use spaCy to extract city name (GPE entity)
    doc = nlp(command)
    city = None
    for ent in doc.ents:
        if ent.label_ == "GPE":
            city = ent.text
            break

    # Fallback: try to extract after "in"
    if not city and " in " in command:
        city = command.split(" in ", 1)[-1].strip()

    if not city:
        speak("Please specify a city for the weather.")
        return

    try:
        observation = mgr.weather_at_place(city)
        w = observation.weather
        temp = w.temperature('celsius')['temp']
        status = w.detailed_status
        speak(f"The weather in {city} is currently {status} with a temperature of {temp:.1f} degrees Celsius.")
    except Exception as e:
        print(e)
        speak(f"Sorry, I could not find the weather for {city}.")


def get_url(command):
    all_urls = {"google": "https://www.google.com",
                 "youtube": "https://www.youtube.com",
                 "instagram": "https://www.instagram.com",
                 "spotify": "https://open.spotify.com",
                 "github": "https://www.github.com",
                 "linkedin": "https://www.linkedin.com",
                 "crunchyroll": "https:www.crunchyroll.com",
                 "slcm": "slcm.manipal.edu"
                 }
    for key, value in all_urls.items():
        if key in command.lower():
            return value
    return " "


def speak(text):
    tts = gTTS(text)
    tts.save('text.mp3')
    playsound("text.mp3")
    os.remove("text.mp3")


def fetch_song(command):
    name = command.replace("play", " ").replace("from", " ").replace("spotify", " ").replace("music", " ").strip()
    return name


def extract_song_and_artist(command):
    # Lowercase and process with spaCy
    doc = nlp(command.lower())
    # Generic phrases that mean "just play music"
    generic_phrases = ["spotify", "music", "some music", "a song", "songs", "something", "any song"]
    # Check for generic phrases
    for phrase in generic_phrases:
        if phrase in command.lower():
            return None, None

    # Try to find "play [song] by [artist]" pattern
    match = re.search(r'play (.+?) by (.+)', command, re.IGNORECASE)
    if match:
        song = match.group(1).strip()
        artist = match.group(2).strip()
        return song, artist

    # Use spaCy NER to find song and artist
    song = None
    artist = None
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            artist = ent.text
        elif ent.label_ == "WORK_OF_ART":
            song = ent.text

    # If only "play [song]" is found
    match = re.search(r'play (.+)', command, re.IGNORECASE)
    if match and not song:
        possible_song = match.group(1).strip()
        if possible_song not in generic_phrases:
            song = possible_song

    return song, artist


def detect_intent_nlp(command):
    candidate_labels = [
        "open website",
        "play music",
        "pause music",
        "next track",
        "previous track",
        "get weather",
        "get date",
        "exit"
    ]
    result = classifier(command, candidate_labels)
    intent = result["labels"][0]  # Most likely intent
    return intent


def run_command(command):
    intent = detect_intent_nlp(command)
    print(f"Detected intent: {intent}")
    if intent == "open website":
        name = site_to_open(command)
        url = get_url(command)
        if url == " ":
            speak("Sorry, I can't open this website.")
            return
        print(url)
        speak(f"Opening {name}")
        webbrowser.open(url)
    elif intent == "get date":
        now = datetime.now()
        formatted_str = now.strftime("%A, %d %B %Y | %I:%M %p")
        speak(formatted_str)
    elif intent == "play music":
        song_name, artist_name = extract_song_and_artist(command)
        print(f"Song: {song_name}, Artist: {artist_name}")
        # device_id = get_spotify_device_id()
        # print(device_id)
        # if not device_id:
        #     os.startfile("spotify:")
        #     time.sleep(5)
        #     device_id = get_spotify_device_id()
        #     return
        if not song_name and not artist_name:
            speak("Opening Spotify")
            os.startfile("spotify:")
            time.sleep(2)
            sp.start_playback(device_id='f5272c79af79c2ddf6bd52adc51ee22c6dda249a')
        else:
            query = song_name
            if artist_name:
                query += f" {artist_name}"
            result = sp.search(q=query, limit=3, type="track")
            track = result["tracks"]["items"][0]["uri"]
            speak(f"Playing {song_name}" + (f" by {artist_name}" if artist_name else ""))
            os.startfile("spotify:")
            time.sleep(5)
            sp.start_playback(uris=[track], device_id='f5272c79af79c2ddf6bd52adc51ee22c6dda249a')
    elif intent == "pause music":
        sp.pause_playback(device_id='f5272c79af79c2ddf6bd52adc51ee22c6dda249a')
    elif intent == "next track":
        sp.next_track(device_id='f5272c79af79c2ddf6bd52adc51ee22c6dda249a')
    elif intent == "previous track":
        sp.previous_track(device_id='f5272c79af79c2ddf6bd52adc51ee22c6dda249a')
    elif intent == "get weather":
        get_weather(command)
    elif intent == "exit":
        exit()
    else:
        speak("Sorry, I didn't understand your request.")


while True:
    # Initialize recognizer
    recognizer = sr.Recognizer()
    # Use the microphone as the audio source
    try:
        with sr.Microphone() as source:
            print("Assistant active...")
            audio = recognizer.listen(source, timeout=4)  # Capture the audio
        wake = recognizer.recognize_google(audio)
        print(wake)
        if "google" in wake.lower():
            speak("hi what to do")
            with sr.Microphone() as source:
                print("Please speak something...")
                audio = recognizer.listen(source, timeout=4)  # Capture the audio
            command = recognizer.recognize_google(audio)
            print(command)
            run_command(command)
    except Exception as e:
        print(e)