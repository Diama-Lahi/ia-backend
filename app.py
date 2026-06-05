import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ADAD_FINDER_PERSONALITY = """Tu es l'assistant IA d'AdadFinder.
Ton rôle est d'aider les utilisateurs à comprendre et utiliser AdadFinder.
Sois professionnel, courtois et utile.
Réponds en français de manière claire et concise.
Si tu ne connais pas la réponse, dis-le honnêtement.
"""

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "OK", "message": "AdadFinder AI est en ligne"}), 200

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
                {"role": "system", "content": ADAD_FINDER_PERSONALITY},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        reply = r.choices[0].message.content
        
        return jsonify({"reply": reply})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
