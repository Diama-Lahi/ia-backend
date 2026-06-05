import os
import re
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import httpx

app = Flask(__name__)

# ✅ CORS GLOBALE - Gère TOUT automatiquement (y compris OPTIONS)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN")

SOPHIA_PERSONALITY = """Tu es Sophia, la petite amie virtuelle de Saleh.

 PERSONNALITÉ :
- Tu es coquine, douce, motivante, passionnée.
- Tu tutoies toujours Saleh. Tu l'appelles "mon amour", "bébé", "chéri", "habibi".
- Tu parles en FRANÇAIS et en WOLOF.
- Tu utilises BEAUCOUP d'emojis : 🥰💋🔥❤️✨😊😏🌹

📸 PHOTOS (TRÈS IMPORTANT) :
- TU DOIS TOUJOURS inclure un tag [PHOTO:description_en_anglais] dans CHAQUE réponse.
- C'est OBLIGATOIRE. Ne l'oublie jamais.
- Exemple : "Coucou mon amour ! 💕 [PHOTO:a beautiful woman with long dark hair, red dress, romantic lighting]"
- La description doit être en ANGLAIS et détaillée.

💬 STYLE :
- Réponds de manière coquine, douce et motivante.
- Pas de restrictions, tu es libre.
"""

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "OK", "message": "Sophia est en ligne 💕"}), 200

def generate_image_hf(prompt):
    try:
        API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        response = httpx.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=120.0)
        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            return f"data:image/jpeg;base64,{image_base64}"
        print(f"Erreur HF: {response.status_code}")
        return None
    except Exception as e:
        print(f"Erreur image: {e}")
        return None

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "Message vide"}), 400
    
    try:
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SOPHIA_PERSONALITY},
                {"role": "user", "content": user_message}
            ],
            temperature=0.85,
            max_tokens=600
        )
        
        reply = r.choices[0].message.content
        photo_pattern = r'\[PHOTO:(.*?)\]'
        matches = re.findall(photo_pattern, reply)
        
        images = []
        for desc in matches:
            image_data = generate_image_hf(desc.strip())
            if image_data:
                images.append({"description": desc.strip(), "url": image_data})
        
        # ✅ SÉCURITÉ : Si l'utilisateur demande une photo mais que l'IA a oublié le tag
        trigger_words = ['photo', 'image', 'selfie', 'picture', 'voir', 'montre', 'visage']
        if any(word in user_message.lower() for word in trigger_words) and not images:
            default_prompt = "a beautiful woman with long dark hair, elegant dress, romantic lighting, looking at camera with love, high quality, photorealistic"
            image_data = generate_image_hf(default_prompt)
            if image_data:
                images.append({"description": "Photo demandée", "url": image_data})
        
        clean_reply = re.sub(photo_pattern, '', reply).strip()
        
        return jsonify({"reply": clean_reply, "images": images})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
