import os
import uuid
import requests
from flask import Flask, send_file, request, jsonify
from gtts import gTTS
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

# Make sure you have a .env file in the same directory with:
# GROQ_API_KEY="YOUR_GROQ_API_KEY"
# GROQ_API_URL="https://api.groq.com/openai/v1/audio/transcriptions"

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL")

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- Serve HTML ----------------
@app.route("/")
def index():
    return send_file("index.html")

# ---------------- Serve TTS files ----------------
@app.route("/tts/<filename>")
def serve_tts(filename):
    tts_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(tts_path):
        return send_file(tts_path, as_attachment=False)
    return "File not found", 404

# ---------------- Transcribe Voice ----------------
@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    # The browser's MediaRecorder sends a .webm file, so we save it as such.
    temp_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.webm")
    file.save(temp_file)

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        with open(temp_file, "rb") as f:
            files = {
                "file": (os.path.basename(temp_file), f, "audio/webm"),
                "model": (None, "whisper-large-v3")
            }
            resp = requests.post(GROQ_API_URL, headers=headers, files=files)

        # Better error handling for the API call
        if resp.status_code != 200:
            return jsonify({"error": f"Groq API Error: {resp.status_code}", "message": resp.text}), resp.status_code

        text = resp.json().get("text", "")
        return jsonify({"text": text})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to connect to Groq API", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "An internal error occurred", "message": str(e)}), 500
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# ---------------- Translate + TTS ----------------
@app.route("/translate_tts", methods=["POST"])
def translate_tts():
    data = request.form
    text = data.get("text")
    lang = data.get("lang")
    if not text or not lang:
        return jsonify({"error": "Missing text or language"}), 400

    try:
        tts_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{lang}.mp3")
        translated_text = GoogleTranslator(source="auto", target=lang).translate(text)
        
        if translated_text is None:
             return jsonify({"error": "Translation failed. The text might be empty or invalid."}), 400

        gTTS(translated_text, lang=lang).save(tts_file)
        return jsonify({"tts_url": f"/tts/{os.path.basename(tts_file)}", "translated_text": translated_text})
        
    except Exception as e:
        return jsonify({"error": "An error occurred during translation or TTS generation", "message": str(e)}), 500

# ---------------- Run Flask ----------------
if __name__ == "__main__":
    print("Starting Flask server at http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)