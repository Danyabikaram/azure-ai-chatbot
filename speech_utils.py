import azure.cognitiveservices.speech as speechsdk
import time
from threading import Lock

# Initialize speech config in config.py and import here if needed

# Rate limiting variables
last_request_time = 0
min_request_interval = 1.0  # Minimum 1 second between requests
rate_limit_lock = Lock()

def recognize_speech(speech_config):
    global last_request_time

    with rate_limit_lock:
        current_time = time.time()
        time_since_last_request = current_time - last_request_time

        if time_since_last_request < min_request_interval:
            sleep_time = min_request_interval - time_since_last_request
            print(f"Rate limiting: waiting {sleep_time:.1f} seconds before next request...")
            time.sleep(sleep_time)

        last_request_time = time.time()

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("Speak into your microphone.")
    max_retries = 3
    for attempt in range(max_retries):
        result = speech_recognizer.recognize_once_async().get()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print(f"Recognized: {result.text}")
            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized.")
            return None
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            print(f"Speech Recognition canceled: {cancellation.reason}")
            if cancellation.reason == speechsdk.CancellationReason.Error:
                print(f"Error details: {cancellation.error_details}")
                if "429" in cancellation.error_details:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Rate limit hit, retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
            return None
#text to speech
def synthesize_speech(speech_config, text):
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized to speaker for text:", text)
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation.reason}")
        if cancellation.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation.error_details}")
