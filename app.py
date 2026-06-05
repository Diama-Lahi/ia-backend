import os
import re
import base64
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import httpx

# ✅ Configuration des logs (pour voir les erreurs dans Render)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN")

logger.info(f"✅ GROQ_API_KEY configurée: {bool(os.getenv('GROQ_API_KEY'))}")
logger.info(f"✅ HF_TOKEN configuré: {bool(HF_TOKEN)}")

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

# ✅ Fonction 1 : Hugging Face (avec token)
def generate_image_hf(prompt):
    try:
        logger.info(f"🎨 Tentative Hugging Face pour: {prompt[:50]}...")
        API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        response = httpx.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=120.0)
        
        logger.info(f"📊 HF Status: {response.status_code}")
        
        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            logger.info("✅ Image HF générée avec succès!")
            return f"data:image/jpeg;base64,{image_base64}"
        else:
            logger.error(f"❌ Erreur HF: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"❌ Exception HF: {str(e)}")
        return None

# ✅ Fonction 2 : Pollinations.ai (gratuit, sans token)
def generate_image_pollinations(prompt):
    try:
        logger.info(f"🎨 Tentative Pollinations pour: {prompt[:50]}...")
        # Pollinations retourne directement l'image
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=768&height=1024&nologo=true&seed=42"
        response = httpx.get(url, timeout=120.0)
        
        logger.info(f"📊 Pollinations Status: {response.status_code}")
        
        if response.status_code == 200 and len(response.content) > 1000:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            logger.info("✅ Image Pollinations générée avec succès!")
            return f"data:image/jpeg;base64,{image_base64}"
        else:
            logger.error(f"❌ Erreur Pollinations: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Exception Pollinations: {str(e)}")
        return None

# ✅ Fonction 3 : Stable Diffusion XL (Hugging Face alternatif)
def generate_image_sdxl(prompt):
    try:
        logger.info(f"🎨 Tentative SDXL pour: {prompt[:50]}...")
        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        response = httpx.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=120.0)
        
        logger.info(f"📊 SDXL Status: {response.status_code}")
        
        if response.status_code == 200:
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            logger.info("✅ Image SDXL générée avec succès!")
            return f"data:image/jpeg;base64,{image_base64}"
        else:
            logger.error(f"❌ Erreur SDXL: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Exception SDXL: {str(e)}")
        return None

# ✅ Fonction principale qui essaie tous les services
def generate_image(prompt):
    logger.info(f"🚀 Début génération image pour: {prompt[:50]}...")
    
    # Essai 1 : Hugging Face FLUX
    image = generate_image_hf(prompt)
    if image:
        return image
    
    # Essai 2 : Stable Diffusion XL
    logger.info("⚠️ FLUX échoué, essai SDXL...")
    image = generate_image_sdxl(prompt)
    if image:
        return image
    
    # Essai 3 : Pollinations (gratuit sans token)
    logger.info("⚠️ SDXL échoué, essai Pollinations...")
    image = generate_image_pollinations(prompt)
    if image:
        return image
    
    logger.error("❌ Tous les services ont échoué!")
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
        logger.info(f"🤖 Réponse IA: {reply[:100]}...")
        
        photo_pattern = r'\[PHOTO:(.*?)\]'
        matches = re.findall(photo_pattern, reply)
        
        images = []
        for desc in matches:
            logger.info(f"📸 Détection photo: {desc[:50]}...")
            image_data = generate_image(desc.strip())
            if image_data:
                images.append({"description": desc.strip(), "url": image_data})
        
        # ✅ SÉCURITÉ : Si l'utilisateur demande une photo mais que l'IA a oublié le tag
        trigger_words = ['photo', 'image', 'selfie', 'picture', 'voir', 'montre', 'visage', 'toi']
        if any(word in user_message.lower() for word in trigger_words) and not images:
            logger.info("⚠️ Photo demandée mais aucun tag détecté, génération forcée...")
            default_prompt = "a beautiful woman with long dark hair, elegant dress, romantic lighting, looking at camera with love, high quality, photorealistic"
            image_data = generate_image(default_prompt)
            if image_data:
                images.append({"description": "Photo demandée", "url": image_data})
        
        clean_reply = re.sub(photo_pattern, '', reply).strip()
        
        logger.info(f"✅ Réponse finale: {len(images)} image(s) générée(s)")
        
        return jsonify({"reply": clean_reply, "images": images})
        
    except Exception as e:
        logger.error(f"❌ Erreur chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
