import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)

# ✅ Client Groq (GRATUIT)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "OK", "message": "Backend IA fonctionne"}), 200

@app.route("/chat", methods=["GET", "POST", "OPTIONS"])
def chat():
    if request.method == "GET":
        return jsonify({"error": "Utilisez POST pour envoyer un message"}), 405
    
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

@app.route("/image-edit", methods=["POST"])
def image_edit():
    return jsonify({"error": "Fonctionnalité image non disponible avec Groq"}), 501

@app.route("/image-variation", methods=["POST"])
def image_variation():
    return jsonify({"error": "Fonctionnalité image non disponible avec Groq"}), 501

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
