"""
app.py — Flask Backend API for AI Code Reviewer
Exposes a POST /analyze endpoint that accepts code and returns analysis as JSON.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from analyzer import analyze_code

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from Streamlit


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "AI Code Reviewer API",
        "version": "1.0.0",
        "endpoints": {
            "POST /analyze": "Analyze code — send JSON with 'code' and optional 'language' fields"
        }
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Expects JSON body:
      {
        "code": "def hello(): ...",
        "language": "python"   // optional, defaults to "python"
      }
    Returns JSON analysis result.
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    code = data.get("code", "")
    language = data.get("language", "python")

    if not code or not code.strip():
        return jsonify({"error": "No code provided. Please include a 'code' field."}), 400

    try:
        result = analyze_code(code, language)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "error": f"Analysis failed: {str(e)}"
        }), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    print("[*] AI Code Reviewer API running on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
