import os

import pygame
import requests
import base64
import sounddevice as sd
import wave
from pathlib import Path
from pydub import AudioSegment
import openai

# Assuming you have these API keys set up in your environment for security.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "insert_api")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "insert_api")


# Set the OpenAI API key
openai.api_key = OPENAI_API_KEY

def record_audio(file_path, sample_rate=48000, channels=1, duration=10):
    print(f"Recording for {duration} seconds...")
    file_path = str(file_path)  # Convert Path object to string
    data = sd.rec(int(sample_rate * duration), samplerate=sample_rate, channels=channels, dtype='int16')
    sd.wait()  # Wait until the recording is finished
    with wave.open(file_path, 'wb') as file:
        file.setnchannels(channels)
        file.setsampwidth(2)  # 16-bit samples
        file.setframerate(sample_rate)
        file.writeframes(data.tobytes())
        print(f"Recorded data size: {len(data) * 2}")  # Each sample is 2 bytes
    print("Recording complete.")

def validate_audio_duration(file_path, expected_duration=5):
    audio = AudioSegment.from_wav(file_path)
    actual_duration = len(audio) / 1000.0  # Convert from milliseconds to seconds
    print(f"Expected duration: {expected_duration}s, Actual duration: {actual_duration}s")
    return actual_duration

def transcribe_audio_google_with_api_key(audio_file_path):
    if not GOOGLE_API_KEY:
        print("Google API key is not set.")
        return []

    print(f"Using Google API Key: {GOOGLE_API_KEY}")

    # Validate audio duration
    actual_duration = validate_audio_duration(audio_file_path)
    if actual_duration != 5:
        print(f"Warning: Actual audio duration is not 10 seconds (it is {actual_duration} seconds).")

    with open(audio_file_path, "rb") as audio_file:
        audio_content = audio_file.read()
        print(f"Audio file size: {len(audio_content)} bytes")
        print(f"First 100 bytes of audio file: {audio_content[:100]}")
        audio_content = base64.b64encode(audio_content).decode("UTF-8")

    url = f"https://speech.googleapis.com/v1/speech:recognize?key={GOOGLE_API_KEY}"
    body = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": 48000,
            "languageCode": "en-US",
            "enableAutomaticPunctuation": True,
            "model": "default"
        },
        "audio": {
            "content": audio_content
        }
    }
    response = requests.post(url, json=body)
    response_data = response.json()

    print("Response from Google Speech-to-Text API:", response_data)

    if response.status_code != 200:
        print(f"Google API Error: {response_data}")
        return []

    if 'results' in response_data:
        transcripts = []
        for result in response_data['results']:
            if 'alternatives' in result and result['alternatives']:
                for alternative in result['alternatives']:
                    if 'transcript' in alternative:
                        transcripts.append(alternative['transcript'])
                    else:
                        print("No transcript found in alternative:", alternative)
        return transcripts
    else:
        print("No results in response data:", response_data)
        return []

def get_openai_response(messages):
    if not OPENAI_API_KEY:
        print("OpenAI API key is not set.")
        return None

    print(f"Using OpenAI API Key: {OPENAI_API_KEY}")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "model": "gpt-4",
        "messages": [{"role": msg["role"], "content": str(msg["content"])} for msg in messages]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        print("Response from OpenAI API:", response_data)

        if 'choices' in response_data:
            return response_data['choices'][0]['message']['content']
        else:
            return None
    except Exception as e:
        print(f"Error fetching response from OpenAI API: {e}")
        return None

def generate_speech(text, speech_file_path):
    if not GOOGLE_API_KEY:
        print("Google API key is not set.")
        return None

    print(f"Using Google API Key: {GOOGLE_API_KEY}")

    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "input": {
            "text": text
        },
        "voice": {
            "languageCode": "en-US",
            "name": "en-US-Wavenet-D"
        },
        "audioConfig": {
            "audioEncoding": "MP3"
        }
    }
    response = requests.post(url, headers=headers, json=body)
    response_data = response.json()

    if 'audioContent' in response_data:
        audio_content = base64.b64decode(response_data['audioContent'])
        with open(speech_file_path, 'wb') as out:
            out.write(audio_content)
    else:
        print(f"Error in generating speech: {response_data}")
        raise Exception("Error in generating speech")

def play_audio(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

if __name__ == "__main__":
    audio_file_path = Path(__file__).parent / "recorded_audio.wav"
    speech_file_path = Path(__file__).parent / "speech.mp3"

    while True:
        record_audio(audio_file_path)
        transcription = transcribe_audio_google_with_api_key(audio_file_path)
        print("Transcription:", transcription)

        if not transcription:
            print("No transcription available. Please try recording again.")
        else:
            system_message = {
                "role": "system",
                "content": "You are my AI assistant."
            }

            user_message = {
                "role": "user",
                "content": transcription
            }

            assistant_response = get_openai_response([system_message, user_message])
            if not assistant_response:
                print("Failed to fetch a response from the model. Please check your API credentials or connectivity.")
            else:
                print("Assistant:", assistant_response)
                generate_speech(assistant_response, speech_file_path)
                play_audio(speech_file_path)
                print(f"Speech generated and played from: {speech_file_path}")
