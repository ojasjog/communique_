import os
import uuid
import requests
from flask import Flask, send_file, request, jsonify
from gtts import gTTS
from dotenv import load_dotenv

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
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    temp_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.wav")
    file.save(temp_file)

    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        files = {"file": open(temp_file, "rb"), "model": (None, "whisper-large-v3")}
        resp = requests.post(GROQ_API_URL, headers=headers, files=files)
        resp.raise_for_status()
        text = resp.json().get("text", "")
    except Exception as e:
        text = f"Error: {str(e)}"
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    return jsonify({"text": text})

# ---------------- Translate + TTS ----------------
@app.route("/translate_tts", methods=["POST"])
def translate_tts():
    text = request.form.get("text")
    lang = request.form.get("lang")
    if not text or not lang:
        return jsonify({"error": "Missing text or language"}), 400

    tts_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{lang}.mp3")
    gTTS(text, lang=lang).save(tts_file)
    return jsonify({"tts_url": f"/tts/{os.path.basename(tts_file)}"})

# ---------------- Run Flask ----------------
if __name__ == "__main__":
    print("Starting Flask server at http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)
