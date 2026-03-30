from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from ai_engine import generate_response
import uuid

load_dotenv()

app = Flask(__name__)
CORS(app)  # Permite conexión desde Vercel

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Brújula API activa ✨"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Falta el campo 'message'"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # Si el frontend no manda user_id, generamos uno de sesión
    user_id = data.get("user_id", f"web_{uuid.uuid4().hex[:8]}")

    try:
        respuesta = generate_response(user_id, user_message)
        return jsonify({
            "reply": respuesta,
            "user_id": user_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
