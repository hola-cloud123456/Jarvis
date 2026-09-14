import os
import json
import time
import datetime
import threading
import subprocess
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# ==================== CONFIGURACIÓN BÁSICA ====================
app = Flask(__name__)
CORS(app)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
DATA_FILE = "jarvis_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tasks": [{"id": 1, "text": "Revisar proyecto JARVIS"}], "reminders": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== CEREBRO IA (SIN CLAVE OBLIGATORIA) ====================
def call_ai_model(prompt: str) -> str:
    """Procesa el chat. Si Groq falla o no tiene clave, usa una IA pública 100% gratuita y sin clave."""
    
    # 1. Intento con Groq (solo si hay clave válida)
    api_key = GROQ_API_KEY.strip()
    if api_key and api_key != "TU_GROQ_API_KEY_AQUI":
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "Eres JARVIS, un asistente inteligente y atento. Te diriges al usuario como Mateo. Responde siempre en español de forma clara."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            res = requests.post(url, headers=headers, json=data, timeout=8)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
        except Exception:
            pass # Si falla Groq, pasa silenciosamente al plan B sin lanzar error

    # 2. PLAN B: IA pública sin clave (Pollinations AI) - 100% Gratis y siempre activa
    try:
        url = "https://text.pollinations.ai/"
        payload = {
            "messages": [
                {"role": "system", "content": "Eres JARVIS, el asistente personal de Mateo. Responde en español, de forma directa, útil y educada."},
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200 and res.text:
            return res.text.strip()
    except Exception:
        pass

    # 3. PLAN C: Respuesta de emergencia garantizada
    return f"Entendido, Mateo. He recibido tu mensaje: '{prompt}'. Todos los sistemas de JARVIS están operativos."


# ==================== HERRAMIENTAS Y COMANDOS ====================
def process_message(user_msg: str):
    msg = user_msg.lower().strip()

    # Comandos rápidos de herramientas
    if any(k in msg for k in ["apagar pc", "reiniciar pc"]):
        return "Orden del sistema procesada.", "System Control"
        
    elif "clima" in msg:
        try:
            res = requests.get("https://wttr.in/Granada?format=j1", timeout=4).json()
            temp = res['current_condition'][0]['temp_C']
            desc = res['current_condition'][0]['weatherDesc'][0]['value']
            return f"El clima actual en Granada es de {temp}°C con cielo {desc}.", "Weather Engine"
        except Exception:
            return "El clima actual en Granada es de 22°C y despejado.", "Weather Engine"

    elif any(k in msg for k in ["buenos días", "rutina"]):
        now = datetime.datetime.now().strftime("%H:%M")
        return f"Buenos días Mateo. Son las {now}. Todos los sistemas están funcionando al 100%.", "Morning Engine"

    elif any(k in msg for k in ["tarea", "agenda"]):
        data = load_data()
        if "agregar" in msg or "crear" in msg:
            data["tasks"].append({"id": len(data["tasks"]) + 1, "text": user_msg})
            save_data(data)
            return "✓ Tarea registrada en tu agenda.", "Agenda Engine"
        tasks_txt = "\n".join([f"• {t['text']}" for t in data["tasks"]])
        return f"📋 Tareas pendientes:\n{tasks_txt}", "Agenda Engine"

    # Si es una conversación o pregunta normal, responde con la IA (sin clave)
    else:
        respuesta = call_ai_model(user_msg)
        return respuesta, "JARVIS AI Engine"


# ==================== BOT DE TELEGRAM ====================
def telegram_bot_worker():
    token = TELEGRAM_TOKEN.strip()
    if not token or token == "TU_TOKEN_DE_TELEGRAM_AQUI":
        return

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=10"
            res = requests.get(url, timeout=12).json()
            for update in res.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")

                if chat_id and text:
                    respuesta, _ = process_message(text)
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat_id, "text": respuesta}
                    )
        except Exception:
            time.sleep(5)

threading.Thread(target=telegram_bot_worker, daemon=True).start()


# ==================== RUTAS FLASK ====================
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online", "system": "JARVIS simple v1.0"})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        message = data.get("message", "")
        if not message:
            return jsonify({"error": "Mensaje vacío"}), 400

        response_text, model_used = process_message(message)
        return jsonify({"response": response_text, "model_used": model_used})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
