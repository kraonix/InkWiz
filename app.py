import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from PIL import Image

# Load environment variables from a .env file for security
load_dotenv()

# --- FLASK APP CONFIGURATION ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

# --- GEMINI API CONFIGURATION ---
try:
    # Configure the Gemini API with the key from the environment
    api_key = os.environ["GEMINI_API_KEY"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set or is empty.")
    genai.configure(api_key=api_key)
except (KeyError, ValueError) as e:
    # Handle missing API key gracefully
    raise SystemExit(f"Error: {e}. Please set your GEMINI_API_KEY in the .env file.")

# Model configuration for consistent output
generation_config = {
    "temperature": 0.3,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 4096,
    # Crucially, ask the model to output JSON
    "response_mime_type": "application/json",
}

# Safety settings to block harmful content
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Initialize the Gemini 1.5 Flash model
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-preview-09-2025",
    generation_config=generation_config,
    safety_settings=safety_settings,
)

def get_processing_prompt(language):
    """
    Generates a language-specific prompt for the Gemini model.
    This prompt instructs the model to perform both OCR and grammar correction
    and to return the result in a structured JSON format.
    """
    prompts = {
        'hindi': """
        आप एक विशेषज्ञ ओसीआर और व्याकरण सुधार उपकरण हैं।
        प्रदान की गई छवि का विश्लेषण करें और दो कार्य करें:
        1. छवि से सभी पाठ को ठीक वैसे ही निकालें जैसा वह दिखाई देता है।
        2. निकाले गए पाठ को लें और सभी वर्तनी और व्याकरण की गलतियों को सुधारें।

        परिणाम को दो कुंजियों के साथ JSON ऑब्जेक्ट के रूप में लौटाएं: "extracted_text" और "corrected_text"।
        JSON ऑब्जेक्ट के बाहर कोई अन्य स्पष्टीकरण या टेक्स्ट शामिल न करें।
        """,
        'english': """
        You are an expert OCR and grammar correction tool.
        Analyze the provided image and perform two tasks:
        1. Extract all the text from the image exactly as it appears.
        2. Take the extracted text and correct all spelling and grammar mistakes.

        Return the result as a JSON object with two keys: "extracted_text" and "corrected_text".
        Do not include any other explanations or text outside of the JSON object.
        """
    }
    return prompts.get(language, prompts['english']) # Default to English

@app.route('/')
def index():
    """Renders the main page of the application."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_image():
    """
    Handles the image upload, processes it with Gemini, and returns the results.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    language = request.form.get('language', 'english')

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        try:
            # Open the image using Pillow
            img = Image.open(file.stream)

            # Get the correct prompt for the selected language
            prompt = get_processing_prompt(language)
            
            # Send the image and prompt to the Gemini model
            response = model.generate_content([prompt, img])
            
            # Parse the JSON response from the model
            result_json = json.loads(response.text)
            
            extracted_text = result_json.get("extracted_text", "")
            corrected_text = result_json.get("corrected_text", "")

            if not extracted_text:
                 return jsonify({"error": "Could not extract any text from the image."}), 400

            return jsonify({
                "extracted_text": extracted_text,
                "corrected_text": corrected_text
            })

        except Exception as e:
            # Log the error for debugging and return a generic error message
            app.logger.error(f"An error occurred during processing: {e}")
            return jsonify({"error": "An internal error occurred. Please try again later."}), 500

if __name__ == '__main__':
    # Run the app in debug mode for development
    # For production, a WSGI server like Gunicorn should be used
    app.run(debug=True)
