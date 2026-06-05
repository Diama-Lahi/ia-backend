import os
from flask import Flask, request, jsonify
from openai import OpenAI
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs("uploads", exist_ok=True)

os.environ["OPENAI_API_KEY"] = "TA_CLE_OPENAI"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user = data.get("message", "")

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user}]
    )
    return jsonify({"reply": r.choices[0].message.content})

@app.route("/image-edit", methods=["POST"])
def image_edit():
    prompt = request.form.get("prompt")
    img = request.files.get("image")

    filename = secure_filename(img.filename)
    path = os.path.join("uploads", filename)
    img.save(path)

    r = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    return jsonify({"image_base64": r.data[0].b64_json})

@app.route("/image-variation", methods=["POST"])
def image_variation():
    img = request.files.get("image")

    filename = secure_filename(img.filename)
    path = os.path.join("uploads", filename)
    img.save(path)

    r = client.images.generate(
        model="gpt-image-1",
        prompt="Variation de l'image fournie",
        size="1024x1024"
    )

    return jsonify({"image_base64": r.data[0].b64_json})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
