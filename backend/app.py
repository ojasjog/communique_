from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from deep_translator import GoogleTranslator
from gtts import gTTS
from faster_whisper import WhisperModel
import os

app = Flask(__name__)
CORS(app)  # allow frontend to call backend if served separately

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load Whisper model once
model = WhisperModel("small")

@app.route("/upload", methods=["POST"])
def upload_audio():
    file = request.files["audio"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Transcribe
    segments, _ = model.transcribe(filepath)
    text = " ".join([seg.text for seg in segments])

    # Translate (English → Hindi as default)
    translated = GoogleTranslator(source="auto", target="hi").translate(text)

    # TTS
    tts_path = os.path.join(OUTPUT_FOLDER, "output.mp3")
    gTTS(translated, lang="hi").save(tts_path)

    return jsonify({
        "original_text": text,
        "translated_text": translated,
        "tts_file": "/download/output.mp3"
    })

@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=False)

if __name__ == "__main__":
    app.run(debug=False)  # no debugger PIN
 