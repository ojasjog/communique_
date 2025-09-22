import os
import uuid
import requests
import asyncio
import edge_tts
import time
from flask import Flask, send_file, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/audio/transcriptions")

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')

# Initialize SocketIO with eventlet async mode
async_mode = 'eventlet'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)

# Uploads folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# User session data
user_data = {}

# Voice mapping for edge-tts
VOICE_MAP = {
    "en": "en-US-JennyNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "it": "it-IT-ElsaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ar": "ar-SA-ZariyahNeural",
    "bn": "bn-BD-NabanitaNeural",
    "ta": "ta-IN-PallaviNeural",
    "tr": "tr-TR-EmelNeural",
    "vi": "vi-VN-HoaiMyNeural",
    "pl": "pl-PL-ZofiaNeural",
    "nl": "nl-NL-FennaNeural",
}

# Async function to generate TTS
async def generate_speech_async(text, voice, file_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)

# Serve frontend
@app.route("/")
def index():
    return send_file("index.html")

# Serve generated TTS
@app.route("/tts/<filename>")
def serve_tts(filename):
    tts_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(tts_path):
        return send_file(tts_path, as_attachment=False)
    return "File not found", 404

# SocketIO connection handlers
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    user_data[request.sid] = {'lang': 'en'}
    join_room('translation_room')

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    if request.sid in user_data:
        del user_data[request.sid]

@socketio.on('set_language')
def handle_set_language(data):
    lang = data.get('lang')
    if request.sid in user_data and lang in VOICE_MAP:
        user_data[request.sid]['lang'] = lang
        print(f"Client {request.sid} set language to {lang}")

@socketio.on('voice_input')
def handle_voice_input(data):
    audio_blob = data.get('audio')
    if not audio_blob:
        return

    temp_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.webm")
    try:
        with open(temp_file, 'wb') as f:
            f.write(audio_blob)

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        with open(temp_file, "rb") as f:
            files = {"file": (os.path.basename(temp_file), f, "audio/webm"), "model": (None, "whisper-large-v3")}
            resp = requests.post(GROQ_API_URL, headers=headers, files=files)

        if resp.status_code != 200:
            print(f"Transcription failed: {resp.text}")
            return

        transcribed_text = resp.json().get("text", "").strip()
        if not transcribed_text:
            print("Transcription produced empty text.")
            return

        for sid, user in user_data.items():
            lang = user['lang']
            translated_text = GoogleTranslator(source="auto", target=lang).translate(transcribed_text)
            if not translated_text:
                continue

            unique_id = uuid.uuid4().hex
            tts_file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_{lang}.mp3")
            voice = VOICE_MAP.get(lang, "en-US-JennyNeural")
            asyncio.run(generate_speech_async(translated_text, voice, tts_file_path))

            emit('translation_output', {
                'transcribed_text': transcribed_text,
                'translated_text': translated_text,
                'tts_url': f"/tts/{os.path.basename(tts_file_path)}"
            }, room=sid)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Optional: cleanup old files
def cleanup_old_files():
    now = time.time()
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.stat(filepath).st_mtime < now - 3600:
            if os.path.isfile(filepath):
                os.remove(filepath)
                print(f"Cleaned up old file: {filepath}")

# Run server
if __name__ == "__main__":
    print("Starting Flask-SocketIO server at http://127.0.0.1:5000 ...")
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
