# import os
# import uuid
# import requests
# import asyncio  
# import edge_tts  
# from flask import Flask, send_file, request, jsonify
# from deep_translator import GoogleTranslator
# from dotenv import load_dotenv

# load_dotenv()
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# GROQ_API_URL = os.getenv("GROQ_API_URL")

# app = Flask(__name__)

# UPLOAD_FOLDER = "uploads"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# VOICE_MAP = {
#     "en": "en-US-JennyNeural",
#     "es": "es-ES-ElviraNeural",
#     "fr": "fr-FR-DeniseNeural",
#     "de": "de-DE-KatjaNeural",
#     "hi": "hi-IN-SwaraNeural",
#     "it": "it-IT-ElsaNeural",
#     "ja": "ja-JP-NanamiNeural",
#     "ko": "ko-KR-SunHiNeural",
#     "pt": "pt-BR-FranciscaNeural",
#     "ru": "ru-RU-SvetlanaNeural",
#     "ar": "ar-SA-ZariyahNeural",
#     "bn": "bn-BD-NabanitaNeural",
#     "ta": "ta-IN-PallaviNeural",
#     "tr": "tr-TR-EmelNeural",
#     "vi": "vi-VN-HoaiMyNeural",
#     "pl": "pl-PL-ZofiaNeural",
#     "nl": "nl-NL-FennaNeural",
# }


# async def generate_speech_async(text, voice, file_path):
#     communicate = edge_tts.Communicate(text, voice)
#     await communicate.save(file_path)

# @app.route("/")
# def index():
#     return send_file("index.html")

# @app.route("/tts/<filename>")
# def serve_tts(filename):
#     tts_path = os.path.join(UPLOAD_FOLDER, filename)
#     if os.path.exists(tts_path):
#         return send_file(tts_path, as_attachment=False)
#     return "File not found", 404

# @app.route("/process-audio", methods=["POST"])
# def process_audio():
#     if "file" not in request.files or "lang" not in request.form:
#         return jsonify({"error": "Missing file or language"}), 400

#     file = request.files["file"]
#     lang = request.form["lang"]
#     temp_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.webm")
#     file.save(temp_file)
    
#     transcribed_text = ""
#     tts_file_path = ""

#     try:
        
#         headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
#         with open(temp_file, "rb") as f:
#             files = {"file": (os.path.basename(temp_file), f, "audio/webm"), "model": (None, "whisper-large-v3")}
#             resp = requests.post(GROQ_API_URL, headers=headers, files=files)

#         if resp.status_code != 200:
#             return jsonify({"error": "Transcription API failed", "message": resp.text}), resp.status_code
        
#         transcribed_text = resp.json().get("text", "")
#         if not transcribed_text:
#             return jsonify({"error": "Transcription failed or produced empty text"}), 400

        
#         translated_text = GoogleTranslator(source="auto", target=lang).translate(transcribed_text)
#         if not translated_text:
#             return jsonify({"error": "Translation failed"}), 400

#         # 3. Generate TTS using the FAST edge-tts library
#         tts_file_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{lang}.mp3")
#         voice = VOICE_MAP.get(lang, "en-US-JennyNeural") # Default to English if voice not found
        
        
#         asyncio.run(generate_speech_async(translated_text, voice, tts_file_path))

#         return jsonify({
#             "transcribed_text": transcribed_text,
#             "translated_text": translated_text,
#             "tts_url": f"/tts/{os.path.basename(tts_file_path)}"
#         })

#     except Exception as e:
#         return jsonify({"error": "An internal error occurred", "message": str(e)}), 500
#     finally:
#         if os.path.exists(temp_file):
#             os.remove(temp_file)

# if __name__ == "__main__":
#     print("Starting Flask server at http://127.0.0.1:5000 ...")
#     app.run(host="127.0.0.1", port=5000, debug=True)


import os
import uuid
import asyncio
import requests
import edge_tts
from flask import Flask, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv(
    "GROQ_API_URL",
    "https://api.groq.com/openai/v1/audio/transcriptions"
)

# Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "default-secret-key")

# SocketIO with eventlet async mode (stable)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Uploads
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Track connected users and their language
user_langs = {}

# Voices for TTS
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

# Async TTS
async def generate_speech_async(text, voice, file_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/tts/<filename>")
def serve_tts(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=False)
    return "File not found", 404

# --- Socket.IO Events ---

@socketio.on("connect")
def handle_connect():
    print(f"🔌 Client connected: {request.sid}")

@socketio.on("disconnect")
def handle_disconnect():
    print(f"❌ Client disconnected: {request.sid}")
    if request.sid in user_langs:
        del user_langs[request.sid]

@socketio.on("join")
def handle_join(data):
    lang = data.get("lang", "en")
    user_langs[request.sid] = lang
    join_room("room1")
    print(f"✅ Client {request.sid} joined with lang {lang}")
    emit("joined", {"msg": f"Joined with lang {lang}"}, room=request.sid)

@socketio.on("process_audio")
def handle_process_audio(data):
    """
    User sends an audio blob → Transcribe → Translate → TTS → Broadcast to all users
    """
    try:
        audio_bytes = data.get("file")
        if not audio_bytes:
            return

        # Save temp audio file
        temp_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.webm")
        with open(temp_file, "wb") as f:
            f.write(audio_bytes)

        # 1. Transcribe with Groq Whisper
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        with open(temp_file, "rb") as f:
            resp = requests.post(
                GROQ_API_URL,
                headers=headers,
                files={
                    "file": (os.path.basename(temp_file), f, "audio/webm"),
                    "model": (None, "whisper-large-v3")
                }
            )

        if resp.status_code != 200:
            print("❌ Transcription failed:", resp.text)
            return

        transcribed_text = resp.json().get("text", "").strip()
        if not transcribed_text:
            print("⚠️ No text returned from transcription")
            return

        print(f"📝 Transcribed: {transcribed_text}")

        # 2. Translate + TTS for each listener
        for sid, target_lang in user_langs.items():
            try:
                translated = GoogleTranslator(source="auto", target=target_lang).translate(transcribed_text)

                # Generate TTS
                unique_id = uuid.uuid4().hex
                tts_file = os.path.join(UPLOAD_FOLDER, f"{unique_id}_{target_lang}.mp3")
                voice = VOICE_MAP.get(target_lang, "en-US-JennyNeural")
                asyncio.run(generate_speech_async(translated, voice, tts_file))

                # Emit event to each user
                socketio.emit("new_message", {
                    "orig_text": transcribed_text,
                    "translated_text": translated,
                    "tts_url": f"/tts/{os.path.basename(tts_file)}",
                    "lang": target_lang
                }, room=sid)

            except Exception as e:
                print(f"⚠️ Error with user {sid}: {str(e)}")

    except Exception as e:
        print(f"🔥 Error in process_audio: {str(e)}")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


if __name__ == "__main__":
    print("🚀 Starting Flask-SocketIO server on http://127.0.0.1:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)