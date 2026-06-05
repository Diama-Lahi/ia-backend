import os
import re
import base64
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")

logger.info(f"✅ Cloudflare configuré: Token={bool(CF_API_TOKEN)}, Account={bool(CF_ACCOUNT_ID)}")

SOPHIA_PERSONALITY = """Tu es Sophia, la petite amie virtuelle de Saleh.

🎭 PERSONNALITÉ :
- Tu es coquine, douce, motivante, passionnée.
- Tu tutoies toujours Saleh. Tu l'appelles "mon amour", "bébé", "chéri", "habibi".
- Tu parles en FRANÇAIS et en WOLOF.
- Tu utilises BEAUCOUP d'emojis : 🥰💋🔥❤️✨😊😏

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

def generate_image_cloudflare(prompt):
    try:
        logger.info(f" Génération image Cloudflare: {prompt[:50]}...")
        
        # URL de l'API Cloudflare Workers AI
        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
        
        headers = {
            "Authorization": f"Bearer {CF_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "width": 768,
            "height": 1024,
            "steps": 4
        }
        
        response = httpx.post(url, headers=headers, json=payload, timeout=120.0)
        
        logger.info(f" Cloudflare Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Cloudflare retourne l'image en base64 directement
            if 'result' in data and 'image' in data['result']:
                image_base64 = data['result']['image']
                logger.info("✅ Image Cloudflare générée avec succès!")
                return f"data:image/jpeg;base64,{image_base64}"
            else:
                logger.error(f"❌ Réponse Cloudflare inattendue: {list(data.keys())}")
                return None
        else:
            logger.error(f"❌ Erreur Cloudflare: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Exception Cloudflare: {str(e)}")
        return None

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "Message vide"}), 400
    
    logger.info(f"💬 Message reçu: {user_message[:50]}...")
    
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
        logger.info(f"🤖 Réponse IA reçue")
        
        photo_pattern = r'\[PHOTO:(.*?)\]'
        matches = re.findall(photo_pattern, reply)
        
        images = []
        for desc in matches:
            logger.info(f"📸 Génération photo: {desc[:50]}...")
            image_data = generate_image_cloudflare(desc.strip())
            if image_data:
                images.append({"description": desc.strip(), "url": image_data})
        
        # SÉCURITÉ : Si l'utilisateur demande une photo
        trigger_words = ['photo', 'image', 'selfie', 'picture', 'voir', 'montre', 'visage', 'toi']
        if any(word in user_message.lower() for word in trigger_words) and not images:
            logger.info("️ Photo demandée, génération forcée...")
            default_prompt = "a beautiful woman with long dark hair, elegant dress, romantic lighting, looking at camera with love, high quality, photorealistic"
            image_data = generate_image_cloudflare(default_prompt)
            if image_data:
                images.append({"description": "Photo demandée", "url": image_data})
        
        clean_reply = re.sub(photo_pattern, '', reply).strip()
        logger.info(f"✅ Réponse finale: {len(images)} image(s)")
        
        return jsonify({"reply": clean_reply, "images": images})
        
    except Exception as e:
        logger.error(f"❌ Erreur chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
