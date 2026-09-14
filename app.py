import json
import logging
import os
import re
import sqlite3
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("JARVIS_DATA_DIR", BASE_DIR / "data"))
DATABASE_PATH = DATA_DIR / "memory.sqlite3"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODELS = [
    item.strip()
    for item in os.environ.get(
        "GROQ_MODELS", "llama-3.3-70b-versatile,llama-3.1-8b-instant"
    ).split(",")
    if item.strip()
]
ACCESS_TOKEN = os.environ.get("JARVIS_ACCESS_TOKEN", "").strip()
ALLOWED_ORIGINS = {
    item.strip().rstrip("/")
    for item in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if item.strip()
}
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", "4000"))
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("jarvis")

_rate_lock = threading.Lock()
_requests_by_ip = defaultdict(deque)
_safe_session_id = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def load_json(filename, fallback):
    try:
        with (BASE_DIR / filename).open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("No se pudo cargar %s: %s", filename, exc)
        return fallback


def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)"
    )
    return connection


def recent_messages(session_id, limit=12):
    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT role, content FROM (
                SELECT id, role, content
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
            """,
            (session_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def save_exchange(session_id, user_message, assistant_message):
    now = int(time.time())
    with get_db() as connection:
        connection.executemany(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            [
                (session_id, "user", user_message, now),
                (session_id, "assistant", assistant_message, now),
            ],
        )


def is_authorized():
    if not ACCESS_TOKEN:
        return True
    authorization = request.headers.get("Authorization", "")
    return authorization == f"Bearer {ACCESS_TOKEN}"


def rate_limit_exceeded():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    client_ip = client_ip.split(",", 1)[0].strip()
    now = time.monotonic()
    with _rate_lock:
        timestamps = _requests_by_ip[client_ip]
        while timestamps and now - timestamps[0] >= 60:
            timestamps.popleft()
        if len(timestamps) >= RATE_LIMIT:
            return True
        timestamps.append(now)
    return False


def protected_endpoint():
    if not is_authorized():
        return jsonify({"error": "Acceso no autorizado."}), 401
    if rate_limit_exceeded():
        return jsonify({"error": "Demasiadas solicitudes. Espera un minuto."}), 429
    return None


def system_prompt():
    profile = load_json("profile.json", {})
    calendar = load_json("calendar.json", [])
    return (
        "Eres JARVIS, el asistente personal de Mateo. Responde siempre en español, "
        "de forma clara, directa, exacta y servicial. No inventes datos del perfil "
        "ni de la agenda. Si falta información, dilo.\n\n"
        f"PERFIL REAL:\n{json.dumps(profile, ensure_ascii=False)}\n\n"
        f"AGENDA REAL:\n{json.dumps(calendar, ensure_ascii=False)}"
    )


def get_groq_response(message, history):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY no está configurada")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = [{"role": "system", "content": system_prompt()}, *history]
    messages.append({"role": "user", "content": message})
    last_status = None

    for model in GROQ_MODELS[:2]:
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.6,
                    "max_tokens": 1024,
                },
                timeout=(5, 20),
            )
            last_status = response.status_code
            if response.ok:
                payload = response.json()
                return payload["choices"][0]["message"]["content"].strip(), model
            if response.status_code in (400, 401, 403, 429):
                break
        except (requests.RequestException, KeyError, ValueError) as exc:
            logger.warning("Fallo de Groq con %s: %s", model, exc)

    logger.error("Groq no respondió correctamente (estado=%s)", last_status)
    raise RuntimeError("El servicio de IA no está disponible en este momento")


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=()"
    origin = request.headers.get("Origin", "").rstrip("/")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "online",
            "system": "JARVIS",
            "groq_configured": bool(GROQ_API_KEY),
            "private_access": bool(ACCESS_TOKEN),
        }
    )


@app.post("/chat")
def chat():
    rejection = protected_endpoint()
    if rejection:
        return rejection

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "La solicitud debe ser JSON."}), 400

    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Escribe un mensaje."}), 400
    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": "El mensaje es demasiado largo."}), 400
    if not isinstance(session_id, str) or not _safe_session_id.fullmatch(session_id):
        return jsonify({"error": "Identificador de sesión no válido."}), 400

    try:
        history = recent_messages(session_id)
        reply, model = get_groq_response(message, history)
        save_exchange(session_id, message, reply)
        return jsonify({"response": reply, "model_used": model})
    except RuntimeError as exc:
        logger.error("No se pudo responder: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception:
        logger.exception("Error inesperado en /chat")
        return jsonify({"error": "Error interno de JARVIS."}), 500


@app.get("/api/calendar")
def calendar():
    rejection = protected_endpoint()
    if rejection:
        return rejection
    events = load_json("calendar.json", [])
    if not isinstance(events, list):
        events = []
    return jsonify({"events": events})


@app.delete("/api/memory/<session_id>")
def clear_memory(session_id):
    rejection = protected_endpoint()
    if rejection:
        return rejection
    if not _safe_session_id.fullmatch(session_id):
        return jsonify({"error": "Identificador de sesión no válido."}), 400
    with get_db() as connection:
        connection.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    return jsonify({"cleared": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
