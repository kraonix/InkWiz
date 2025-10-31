import os
import json
import base64
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB


# --- GEMINI CONFIG ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("❌ GEMINI_API_KEY missing. Set it in .env or Render env vars.")

genai.configure(api_key=api_key)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    generation_config={
        "temperature": 0.2,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 4096,
        "response_mime_type": "application/json",
    }
)


# Prompts
def get_processing_prompt(language):
    if language == "hindi":
        return """
        आप एक विशेषज्ञ OCR और व्याकरण सुधार प्रणाली हैं।
        छवि से टेक्स्ट ज्यों का त्यों निकालें और फिर उसे सही करें।

        JSON आउटपुट:
        {
            "extracted_text": "...",
            "corrected_text": "..."
        }
        """
    return """
    You are an expert OCR + grammar correction tool.
    Extract text exactly as in image, then correct grammar.

    JSON output strictly:
    {
        "extracted_text": "...",
        "corrected_text": "..."
    }
    """


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_image():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    language = request.form.get("language", "english")

    if file.filename == "":
        return jsonify({"error": "Empty file name."}), 400

    try:
        # ✅ Read file ONCE
        file_bytes = file.read()

        if len(file_bytes) == 0:
            return jsonify({"error": "Uploaded file is empty."}), 400

        # ✅ Convert to base64 for Gemini
        img_base64 = base64.b64encode(file_bytes).decode("utf-8")

        prompt = get_processing_prompt(language)

        # ✅ Gemini Request
        response = model.generate_content([
            prompt,
            {
                "mime_type": "image/jpeg",
                "data": img_base64
            }
        ])

        # ✅ Extract text safely
        try:
            raw_text = response.candidates[0].content.parts[0].text
        except:
            raw_text = response.text

        # Clean JSON
        clean_text = (
            raw_text.replace("```json", "")
                    .replace("```", "")
                    .strip()
        )

        result_json = json.loads(clean_text)

        return jsonify({
            "extracted_text": result_json.get("extracted_text", ""),
            "corrected_text": result_json.get("corrected_text", "")
        })

    except Exception as e:
        app.logger.error(f"🔥 INTERNAL ERROR: {e}")
        return jsonify({"error": "Internal server error."}), 500


if __name__ == "__main__":
    app.run(debug=True)
