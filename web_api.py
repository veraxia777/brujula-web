from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from ai_engine import generate_response
import uuid
import re

load_dotenv()
app = Flask(__name__)
CORS(app)  # Permite conexión desde Vercel

# ------------------------------------------------------------
# CAPA DE CRISIS (lado del servidor) — respaldo del frontend
# Detecta señales de riesgo aunque el navegador falle o alguien
# use la API directamente. Recursos verificados (julio 2026).
# ------------------------------------------------------------
CRISIS_PATTERNS = [
    r"\b(kill myself|end my life|want to die|suicid|don'?t want to (live|be here)|"
    r"better off dead|no reason to live|hurt myself|harm myself|take my (own )?life)\b",
    r"\b(suicid|quiero morir|me quiero morir|matarme|acabar con mi vida|"
    r"terminar con mi vida|no quiero vivir|no quiero seguir|hacerme daño|"
    r"quitarme la vida|no vale la pena vivir)\b",
    r"\b(suic[ií]d|quero morrer|me matar|acabar com minha vida|"
    r"n[ãa]o quero viver|n[ãa]o quero mais viver|me machucar|tirar minha vida)\b",
]
_CRISIS_RE = [re.compile(p, re.IGNORECASE) for p in CRISIS_PATTERNS]


def is_crisis(text):
    return any(rx.search(text or "") for rx in _CRISIS_RE)


CRISIS_REPLY = {
    "es": (
        "Antes de seguir, quiero que sepas algo importante: no tienes que pasar por "
        "esto solo/a. Si estás pensando en hacerte daño, por favor habla ahora con "
        "alguien preparado para acompañarte:\n\n"
        "• Chile: *4141 (Línea Prevención del Suicidio, gratis y 24/7)\n"
        "• Chile: Salud Responde 600 360 7777, opción 2\n"
        "• EE.UU.: 988 (llama o textea; en español marca 988 y presiona 2)\n"
        "• Cualquier país: findahelpline.com\n\n"
        "Si estás en peligro inmediato, contacta a emergencias (131 en Chile, 911 en EE.UU.).\n\n"
        "Estoy aquí contigo. ¿Quieres contarme qué está pasando?"
    ),
    "en": (
        "Before we go on, I want you to know something important: you don't have to "
        "go through this alone. If you're thinking about harming yourself, please talk "
        "to someone trained to help right now:\n\n"
        "• USA: 988 (call or text, free & 24/7)\n"
        "• Any country: findahelpline.com\n\n"
        "If you're in immediate danger, please contact emergency services (911 in the US).\n\n"
        "I'm here with you. Do you want to tell me what's going on?"
    ),
    "pt": (
        "Antes de continuarmos, quero que você saiba algo importante: você não precisa "
        "passar por isso sozinho. Se você está pensando em se machucar, por favor fale "
        "agora com alguém preparado para te ajudar:\n\n"
        "• EUA: 988 (ligue ou envie mensagem)\n"
        "• Qualquer país: findahelpline.com\n\n"
        "Se você está em perigo imediato, contate os serviços de emergência.\n\n"
        "Estou aqui com você. Quer me contar o que está acontecendo?"
    ),
}


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

    user_id = data.get("user_id", f"web_{uuid.uuid4().hex[:8]}")
    lang = data.get("lang", "es")
    silent = data.get("silent", False)

    # 1) Mensaje "silent" de contexto (categoría elegida en el frontend).
    #    No debe generar respuesta visible. Se pasa como contexto al motor
    #    para que la próxima respuesta ya sepa de qué se trata.
    if silent or user_message.startswith("[context]"):
        try:
            # Se envía al motor marcado como contexto; devolvemos vacío al frontend.
            generate_response(user_id, user_message)
        except Exception:
            pass
        return jsonify({"reply": "", "silent": True, "user_id": user_id})

    # 2) Detección de crisis del lado del servidor (respaldo).
    #    Aunque el modelo respondiera mal, el usuario recibe recursos reales.
    if is_crisis(user_message):
        return jsonify({
            "reply": CRISIS_REPLY.get(lang, CRISIS_REPLY["es"]),
            "crisis": True,
            "user_id": user_id
        })

    # 3) Flujo normal.
    try:
        respuesta = generate_response(user_id, user_message)
        return jsonify({"reply": respuesta, "user_id": user_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------
# Endpoints que el frontend ya llama (antes fallaban en silencio).
# Guardado mínimo; ajusta a tu base de datos si más adelante quieres persistir.
# ------------------------------------------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    user_id = data.get("user_id", f"web_{uuid.uuid4().hex[:8]}")
    # TODO: si quieres, guarda aquí name/email/user_id en tu base de datos.
    print(f"[register] {user_id} | {name} | {email}")
    return jsonify({"ok": True, "user_id": user_id})


@app.route("/track-click", methods=["POST"])
def track_click():
    data = request.get_json() or {}
    event = (data.get("event") or "").strip()
    user_id = data.get("user_id", "anon")
    print(f"[track-click] {user_id} | {event}")
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

