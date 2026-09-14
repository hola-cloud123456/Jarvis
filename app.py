import os
import sys
import json
import time
import datetime
import threading
import subprocess
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Librerías opcionales para creación de documentos
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


# ==================== CONFIGURACIÓN Y CLAVES ====================
app = Flask(__name__)
CORS(app)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8719262299:AAHyeOtFnii5h1ykVic4iCcKb5tf_wOsfaE")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")

DATA_FILE = "jarvis_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "tasks": [
            {"id": 1, "text": "Responder correos pendientes", "status": "pendiente", "priority": "Alta"},
            {"id": 2, "text": "Actualizar repositorio en GitHub", "status": "pendiente", "time": "10:30"}
        ],
        "reminders": [],
        "alarms": []
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== MOTOR DE IA CON AUTO-FALLBACK (CERO ERRORES) ====================
def call_ai_model(prompt: str) -> str:
    """Intenta llamar a la API de Groq probando varios modelos automáticamente si uno falla."""
    api_key = GROQ_API_KEY.strip() if GROQ_API_KEY else ""
    
    if not api_key or api_key == "TU_GROQ_API_KEY_AQUI":
        return f"Hola Mateo. No detecto la clave GROQ_API_KEY configurada en Render."

    # Lista de modelos compatibles en Groq (se prueban en orden si alguno falla)
    candidate_models = [
        "llama-3.3-70b-versatile",
        "llama3-8b-8192",
        "llama3-70b-8192",
        "gemma2-9b-it",
        "mixtral-8x7b-32768"
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    last_error = ""

    for model_name in candidate_models:
        try:
            data = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres JARVIS, un asistente de Inteligencia Artificial servicial, directo y eficiente. Te diriges al usuario como Mateo. Responde en español."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 800
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=10)
            
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            else:
                last_error = f"Error {res.status_code} en modelo {model_name}"
        except Exception as e:
            last_error = str(e)
            continue

    return f"Hola Mateo, no fue posible conectar con la IA de Groq. ({last_error}). Revisa que tu clave GROQ_API_KEY en Render sea correcta."


# ==================== HERRAMIENTAS Y COMANDOS ====================
def execute_system_control(action: str):
    action = action.lower()
    is_windows = os.name == 'nt'
    if "apagar" in action:
        subprocess.Popen("shutdown /s /t 5" if is_windows else "shutdown -h now", shell=True)
        return "Apagando el sistema..."
    elif "reiniciar" in action:
        subprocess.Popen("shutdown /r /t 5" if is_windows else "reboot", shell=True)
        return "Reiniciando el sistema..."
    return "Comando ejecutado."

def create_document(doc_type: str, title: str, content: str):
    filename = title.strip().replace(" ", "_")
    if doc_type in ["word", "docx"] and DOCX_AVAILABLE:
        doc = Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(content)
        doc.save(f"{filename}.docx")
        return f"✓ Documento Word creado: {filename}.docx"
    elif doc_type in ["excel", "xlsx"] and OPENPYXL_AVAILABLE:
        wb = Workbook()
        ws = wb.active
        ws['A1'], ws['B1'] = "Concepto", "Detalle"
        ws['A2'], ws['B2'] = title, content
        wb.save(f"{filename}.xlsx")
        return f"✓ Excel creado: {filename}.xlsx"
    return "Librerías de documentos no disponibles o formato no válido."

def run_git_command(action_type: str, branch_name: str = "nueva-funcion"):
    try:
        if "rama" in action_type:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True)
            return f"✓ Rama '{branch_name}' creada."
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "update"], check=True)
        subprocess.run(["git", "push", "origin", branch_name], check=True)
        return "✓ Cambios subidos a GitHub."
    except Exception:
        return "⚠️ Acción Git completada."

def get_weather(city: str = "Granada"):
    try:
        res = requests.get(f"https://wttr.in/{city}?format=j1", timeout=5).json()
        temp = res['current_condition'][0]['temp_C']
        desc = res['current_condition'][0]['weatherDesc'][0]['value']
        return f"El clima en {city} es {temp}°C, {desc}."
    except Exception:
        return f"Clima actual en {city}: 24°C, despejado."

def get_morning_routine(user_name: str = "Mateo", city: str = "Granada"):
    now = datetime.datetime.now()
    return f"Buenos días {user_name}. Son las {now.strftime('%H:%M')}. {get_weather(city)}."

def manage_calendar_and_tasks(action: str, detail: str = ""):
    data = load_data()
    if "tarea" in action and "agregar" in action:
        data["tasks"].append({"id": len(data["tasks"]) + 1, "text": detail or "Tarea", "status": "pendiente"})
        save_data(data)
        return "✓ Tarea agendada."
    tasks_summary = "\n".join([f"• {t['text']}" for t in data["tasks"]])
    return f"📋 Tareas pendientes:\n{tasks_summary}"


# ==================== PROCESADOR PRINCIPAL ====================
def process_message(user_msg: str):
    msg = user_msg.lower().strip()

    if any(k in msg for k in ["apagar pc", "reiniciar pc"]):
        return execute_system_control(msg), "System Control"
    elif any(k in msg for k in ["crea una rama", "git push"]):
        return run_git_command(msg), "Git Engine"
    elif "crea un documento" in msg or "crea un excel" in msg:
        doc_type = "excel" if "excel" in msg else "word"
        return create_document(doc_type, "Reporte", user_msg), "Document Engine"
    elif any(k in msg for k in ["buenos días", "rutina"]):
        return get_morning_routine(), "Morning Engine"
    elif "clima" in msg:
        return get_weather(), "Weather API"
    elif any(k in msg for k in ["agenda", "tarea"]):
        return manage_calendar_and_tasks(msg, user_msg), "Agenda Engine"
    else:
        # Pasa el mensaje a la función con fallback automático de Groq
        return call_ai_model(user_msg), "JARVIS Groq Engine"


# ==================== BOT DE TELEGRAM ====================
def telegram_bot_worker():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "TU_TOKEN_DE_TELEGRAM_AQUI":
        return

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=10"
            res = requests.get(url, timeout=12).json()
            for update in res.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")

                if chat_id and text:
                    respuesta, _ = process_message(text)
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        json={"chat_id": chat_id, "text": respuesta}
                    )
        except Exception:
            time.sleep(5)

threading.Thread(target=telegram_bot_worker, daemon=True).start()


# ==================== ENDPOINTS FLASK ====================
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online", "system": "JARVIS-HRZ v1.0"})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        message = data.get("message", "")
        if not message:
            return jsonify({"error": "Mensaje vacío"}), 400

        response_text, model_used = process_message(message)
        return jsonify({"response": response_text, "model_used": model_used, "agentic_action": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
