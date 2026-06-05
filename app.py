import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ✅ Configuration CORS complète pour autoriser ton site GitHub Pages
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://diama-lahi.github.io",
            "https://diama-lahi.github.io/sophia-ai",
            "https://diama-lahi.github.io/sophia-ai/",
            "http://localhost:*",
            "*"
        ],
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": False,
        "max_age": 600
    }
})

app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)

# ✅ Client Groq (GRATUIT)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ✅ Route racine
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "OK",
        "message": "Backend IA fonctionne avec Groq",
        "endpoints": ["/chat", "/image-edit", "/image-variation"]
    }), 200

# ✅ Route OPTIONS explicite pour /chat (préflight CORS)
@app.route("/chat", methods=["OPTIONS"])
def chat_options():
    response = jsonify({"status": "ok"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    return response, 200

# ✅ Route chat - accepte JSON ET form-data
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return jsonify({"error": "Utilisez POST pour envoyer un message"}), 405
    
    # Supporte les deux formats
    if request.is_json:
        data = request.get_json()
        user_message = data.get("message", "")
    else:
        user_message = request.form.get("message", "")
    
    if not user_message:
        return jsonify({"error": "Message vide"}), 400
    
    try:
        # ✅ Utilise Groq avec Llama 3.3 (gratuit)
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": user_message}]
        )
        return jsonify({"reply": r.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Route image-edit (non fonctionnel avec Groq, mais garde la route)
@app.route("/image-edit", methods=["POST", "OPTIONS"])
def image_edit():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response, 200
    
    return jsonify({"error": "Fonctionnalité image non disponible avec Groq"}), 501

# ✅ Route image-variation (non fonctionnel avec Groq, mais garde la route)
@app.route("/image-variation", methods=["POST", "OPTIONS"])
def image_variation():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response, 200
    
    return jsonify({"error": "Fonctionnalité image non disponible avec Groq"}), 501

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
