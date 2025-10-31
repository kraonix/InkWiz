import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()

# --- FLASK CONFIG ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit


# --- GEMINI CONFIG ---
try:
    api_key = os.environ["GEMINI_API_KEY"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is empty.")
    genai.configure(api_key=api_key)
except Exception as e:
    raise SystemExit(f"Error: {e}. Set GEMINI_API_KEY in the .env file.")


generation_config = {
    "temperature": 0.2,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 4096,
    "response_mime_type": "application/json",
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# ✅ Use latest model
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    generation_config=generation_config,
    safety_settings=safety_settings,
)


# --- PROMPTS ---
def get_processing_prompt(language):
    prompts = {
        'hindi': """
        आप एक विशेषज्ञ ओसीआर और व्याकरण सुधार उपकरण हैं।
        छवि का विश्लेषण करें:
        1. टेक्स्ट निकालें (exact).
        2. व्याकरण और वर्तनी ठीक करें।

        आउटपुट JSON होना चाहिए:
        {
            "extracted_text": "...",
            "corrected_text": "..."
        }
        """,

        'english': """
        You are an expert OCR + grammar correction tool.
        Extract the text exactly as it appears.
        Then fix grammar/spelling.

        Output STRICT JSON:
        {
            "extracted_text": "...",
            "corrected_text": "..."
        }
        """
    }
    return prompts.get(language, prompts["english"])


# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    language = request.form.get("language", "english")

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        # Open image
        img = Image.open(file.stream)

        # Gemini response
        prompt = get_processing_prompt(language)
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": file.read()}
        ])

        # ✅ Extract response text from new SDK format
        raw_text = response.candidates[0].content.parts[0].text

        # ✅ Remove accidental markdown or code fences
        clean_text = (
            raw_text.replace("```json", "")
                    .replace("```", "")
                    .strip()
        )

        # ✅ Safe JSON parsing
        result_json = json.loads(clean_text)

        extracted = result_json.get("extracted_text", "")
        corrected = result_json.get("corrected_text", "")

        if not extracted:
            return jsonify({"error": "No text extracted from image."}), 400

        return jsonify({
            "extracted_text": extracted,
            "corrected_text": corrected
        })

    except Exception as e:
        app.logger.error(f"❌ INTERNAL ERROR: {e}")
        return jsonify({"error": "An internal error occurred. Try again later."}), 500


if __name__ == "__main__":
    app.run(debug=True)
