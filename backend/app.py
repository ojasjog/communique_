# app.py
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from deep_translator import GoogleTranslator
from gtts import gTTS
from faster_whisper import WhisperModel
from werkzeug.utils import secure_filename
import os
import uuid

app = Flask(__name__, static_folder=None)
CORS(app)

BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load Whisper model once (force float32 for CPU)
model = WhisperModel("small", compute_type="float32")

@app.route("/")
def index():
    
    return send_file(os.path.join(BASE_DIR, "index.html"))

# Transcribe endpoint
@app.route("/transcribe", methods=["POST"])
def transcribe():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        from werkzeug.utils import secure_filename
        import uuid

        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        segments, _ = model.transcribe(filepath)
        text = " ".join([seg.text.strip() for seg in segments]).strip()

        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Translate + TTS endpoint
@app.route("/translate_tts", methods=["POST"])
def translate_tts():
    text = request.form.get("text")
    target_lang = request.form.get("lang", "en")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Translate
    translated = GoogleTranslator(source="auto", target=target_lang).translate(text)

    # Create unique tts filename
    tts_filename = f"tts_{uuid.uuid4().hex}.mp3"
    tts_path = os.path.join(OUTPUT_FOLDER, tts_filename)

    # Generate TTS
    gTTS(translated, lang=target_lang).save(tts_path)

    # Return the audio file directly (frontend expects a blob)
    return send_file(tts_path, mimetype="audio/mpeg", as_attachment=False)

# Download endpoint
@app.route("/download/<filename>")
def download(filename):
    safe = secure_filename(filename)
    full = os.path.join(OUTPUT_FOLDER, safe)
    if not os.path.exists(full):
        return "Not found", 404
    return send_file(full, mimetype="audio/mpeg", as_attachment=False)

if __name__ == "__main__":
    
    app.run(host="127.0.0.1", port=5000, debug=False)
