import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # Important pour les requêtes cross-origin
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)

# ✅ Récupère la clé depuis les variables d'environnement Render
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Route racine
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "OK", "message": "Backend IA fonctionne"}), 200

# ✅ Route chat - accepte JSON ET form-data
@app.route("/chat", methods=["GET", "POST", "OPTIONS"])
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
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_message}]
        )
        return jsonify({"reply": r.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/image-edit", methods=["POST"])
def image_edit():
    prompt = request.form.get("prompt")
    img = request.files.get("image")
    
    if not img or not prompt:
        return jsonify({"error": "Image et prompt requis"}), 400
    
    filename = secure_filename(img.filename)
    path = os.path.join("uploads", filename)
    img.save(path)
    
    try:
        with open(path, "rb") as image_file:
            r = client.images.edit(
                model="gpt-image-1",
                image=image_file,
                prompt=prompt,
                size="1024x1024"
            )
        return jsonify({"image_base64": r.data[0].b64_json})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/image-variation", methods=["POST"])
def image_variation():
    img = request.files.get("image")
    
    if not img:
        return jsonify({"error": "Image requise"}), 400
    
    filename = secure_filename(img.filename)
    path = os.path.join("uploads", filename)
    img.save(path)
    
    try:
        with open(path, "rb") as image_file:
            r = client.images.create_variation(
                model="gpt-image-1",
                image=image_file,
                size="1024x1024"
            )
        return jsonify({"image_base64": r.data[0].b64_json})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
