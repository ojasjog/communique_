from flask import Flask, request, jsonify, send_file
import os
import subprocess
from gtts import gTTS
from googletrans import Translator

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'tts_output'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)

translator = Translator()

# ------------------ Transcription ------------------
@app.route("/transcribe", methods=["POST"])
def transcribe():
    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Whisper CLI transcription
    subprocess.run(
        ["whisper", file_path, "--model", "base", "--output_format", "txt"],
        capture_output=True
    )

    txt_file_path = file_path.rsplit(".", 1)[0] + ".txt"
    with open(txt_file_path, "r") as f:
        text = f.read()

    return jsonify({"text": text})

# ------------------ Translation + TTS ------------------
@app.route("/translate_tts", methods=["POST"])
def translate_tts():
    text = request.form.get("text")
    target_lang = request.form.get("lang", "en")  # default to English
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Translate
    translated = translator.translate(text, dest=target_lang).text

    # TTS
    tts_file = os.path.join(OUTPUT_FOLDER, "speech.mp3")
    tts = gTTS(text=translated, lang=target_lang)
    tts.save(tts_file)

    return send_file(tts_file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)