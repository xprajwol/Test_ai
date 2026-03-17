import datetime
import os
import sys
import webbrowser
from typing import Optional
from urllib.parse import quote_plus

import pyttsx3
import speech_recognition as sr

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


WELCOME_MESSAGE = "Hello, I am your Python Jarvis. How can I help you?"

NOTES_DIR = os.path.join(os.path.expanduser("~"), "JarvisNotes")

WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "stack overflow": "https://stackoverflow.com",
}

APPS_TO_CLOSE = {
    "notepad": "notepad.exe",
    "calculator": "Calculator.exe",
    "chrome": "chrome.exe",
    "browser": "chrome.exe",
    "edge": "msedge.exe",
}

EXIT_KEYWORDS = [
    "exit",
    "quit",
    "stop",
    "goodbye",
    "bye",
    "close jarvis",
    "shutdown jarvis",
    "turn off jarvis",
]

_tts_engine: Optional[pyttsx3.Engine] = None
_recognizer = sr.Recognizer()


def _get_tts_engine() -> pyttsx3.Engine:
    global _tts_engine
    if _tts_engine is None:
        engine = pyttsx3.init()
        engine.setProperty("rate", 180)
        engine.setProperty("volume", 1.0)
        voices = engine.getProperty("voices")
        if voices:
            engine.setProperty("voice", voices[0].id)
        _tts_engine = engine
    return _tts_engine


def speak(text: str) -> None:
    engine = _get_tts_engine()
    print(f"Jarvis: {text}")
    engine.say(text)
    engine.runAndWait()


def listen() -> Optional[str]:
    with sr.Microphone() as source:
        print("\n🎧  Listening...")
        _recognizer.pause_threshold = 1
        audio = _recognizer.listen(source, phrase_time_limit=8)

    try:
        print("🧠 Recognizing...")
        query = _recognizer.recognize_google(audio, language="en-US")
        query = query.lower()
        print(f"You said: {query}")
        return query
    except sr.UnknownValueError:
        print("Sorry, I did not catch that.")
        return None
    except sr.RequestError as e:
        print(f"Speech recognition service error: {e}")
        return None


def open_website(command: str) -> bool:
    for name, url in WEBSITES.items():
        if name in command:
            speak(f"Opening {name}")
            webbrowser.open(url)
            return True
    return False


def search_web(command: str) -> bool:
    if "search" not in command and "youtube" not in command and "google" not in command:
        return False

    text = command

    engine = "google"
    if "youtube" in text:
        engine = "youtube"
    elif "google" in text:
        engine = "google"

    for token in ["search", "youtube", "google", "on youtube", "on google", "for", "about"]:
        text = text.replace(token, " ")

    query = " ".join(text.split()).strip()
    if not query:
        return False

    q = quote_plus(query)

    if engine == "youtube":
        url = f"https://www.youtube.com/results?search_query={q}"
        speak(f"Searching YouTube for {query}")
    else:
        url = f"https://www.google.com/search?q={q}"
        speak(f"Searching Google for {query}")

    webbrowser.open(url)
    return True


def tell_time() -> None:
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The time is {now}")


def tell_date() -> None:
    today = datetime.date.today()
    speak(f"Today is {today.strftime('%A, %B %d, %Y')}")


def small_talk(command: str) -> bool:
    if "how are you" in command:
        speak("I am functioning optimally. How can I help you today?")
        return True
    if "who are you" in command or "what are you" in command:
        speak("I am your personal Python assistant, similar to Jarvis.")
        return True
    if "thank you" in command or "thanks" in command:
        speak("You are welcome.")
        return True
    return False


def control_system(command: str) -> bool:
    if "open notepad" in command:
        speak("Opening Notepad")
        os.system("start notepad")
        return True
    if "open calculator" in command:
        speak("Opening Calculator")
        os.system("start calc")
        return True
    if "shutdown computer" in command or ("shutdown" in command and "computer" in command):
        speak("Shutting down the computer. Goodbye.")
        os.system("shutdown /s /t 5")
        return True
    return False


def _ensure_notes_dir() -> None:
    os.makedirs(NOTES_DIR, exist_ok=True)


def _append_to_note_file(note_path: str, content: str) -> str:
    _ensure_notes_dir()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(note_path, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {content}\n")
    return note_path


def handle_notepad_note(command: str) -> bool:
    triggers = [
        "new note",
        "create note",
        "make a note",
        "write a note",
        "write in notepad",
        "new file in notepad",
        "make new file",
    ]
    if not any(t in command for t in triggers):
        return False

    speak("What should I name this note?")
    name = listen()
    if not name:
        speak("I did not catch the name. I will call it 'quick note'.")
        name = "quick note"

    safe = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "-", "_")).strip()
    if not safe:
        safe = "note"
    filename = safe.replace(" ", "_") + ".txt"

    _ensure_notes_dir()
    path = os.path.join(NOTES_DIR, filename)

    speak(f"Note mode started for {safe}. I am listening. Say 'exit note' when you are done.")
    os.system(f'start notepad "{path}"')

    while True:
        content = listen()
        if not content:
            continue

        if "exit note" in content or "stop note" in content or "close note" in content:
            speak("Exiting note mode. I am ready for other commands.")
            break

        _append_to_note_file(path, content)
        speak("Added to your note.")

    return True


def close_application(command: str) -> bool:
    if "close" not in command:
        return False

    for name, exe in APPS_TO_CLOSE.items():
        if name in command:
            speak(f"Closing {name}")
            os.system(f"taskkill /f /im {exe}")
            return True

    return False


def init_openai_client():
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def ask_llm(client, prompt: str) -> str:
    if client is None:
        return "I am not connected to the OpenAI service right now."
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly AI assistant called Jarvis. Keep replies short and conversational.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or "I'm not sure how to answer that."
    except Exception:
        return "I'm having trouble reaching my AI brain right now."


def main() -> None:
    client = init_openai_client()

    print("=" * 50)
    print("🤖  JARVIS VOICE ASSISTANT (Python)")
    print("=" * 50)
    speak(WELCOME_MESSAGE)

    while True:
        command = listen()
        if not command:
            continue

        if any(word in command for word in EXIT_KEYWORDS):
            speak("Goodbye. Shutting down.")
            break

        if search_web(command):
            continue
        if open_website(command):
            continue
        if control_system(command):
            continue
        if handle_notepad_note(command):
            continue
        if close_application(command):
            continue
        if "time" in command:
            tell_time()
            continue
        if "date" in command or "today" in command:
            tell_date()
            continue
        if small_talk(command):
            continue

        answer = ask_llm(client, command)
        speak(answer)


if __name__ == "__main__":
    main()