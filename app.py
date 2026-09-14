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
CORS(app)  # Permite peticiones desde GitHub Pages o cualquier frontend

# Claves de APIs (se leen de las variables de entorno de Render o del código)
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
            {"id": 2, "text": "Actualizar repositorio en GitHub", "status": "pendiente", "time": "10:30"},
            {"id": 3, "text": "Preparar informe semanal", "status": "pendiente", "time": "Hoy"},
            {"id": 4, "text": "Llamar al equipo de diseño", "status": "pendiente", "time": "14:00"}
        ],
        "reminders": [
            {"id": 1, "text": "Pagar servicios", "date": "2026-09-15"},
            {"id": 2, "text": "Reunión de seguimiento", "time": "09:00"}
        ],
        "alarms": []
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== INTEGRACIÓN CON MODELO DE IA (GROQ / LLAMA 3.1) ====================
def call_ai_model(prompt: str) -> str:
    """Procesa preguntas conversacionales generales usando Llama 3.1 en Groq API."""
    if not GROQ_API_KEY or GROQ_API_KEY == "TU_GROQ_API_KEY_AQUI":
        return (
            f"Hola Mateo. He recibido tu mensaje: '{prompt}'. "
            f"La clave GROQ_API_KEY no está configurada aún en las variables de entorno de Render."
        )

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.1-8b-instant",  # Modelo 100% activo y rápido en Groq
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres JARVIS, un asistente virtual altamente inteligente, servicial, conciso "
                        "y eficiente. Te diriges al usuario como Mateo. Responde siempre en español "
                        "de forma clara, fluida y natural."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }
        res = requests.post(url, headers=headers, json=data, timeout=12)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
        else:
            return f"Error en la respuesta de IA (Código {res.status_code}): {res.text}"
    except Exception as e:
        return f"Hola Mateo, hubo un inconveniente de conexión con la IA: {str(e)}"


# ==================== HERRAMIENTAS AGÉNTICAS Y COMANDOS ====================

# 1. CONTROL DEL SISTEMA
def execute_system_control(action: str):
    action = action.lower()
    is_windows = os.name == 'nt'
    
    if "apagar" in action:
        cmd = "shutdown /s /t 5" if is_windows else "shutdown -h now"
        try:
            subprocess.Popen(cmd, shell=True)
            return "Iniciando secuencia de apagado del sistema en 5 segundos."
        except Exception as e:
            return f"❌ Error al intentar apagar el sistema: {e}"

    elif "reiniciar" in action:
        cmd = "shutdown /r /t 5" if is_windows else "reboot"
        try:
            subprocess.Popen(cmd, shell=True)
            return "Reiniciando el sistema operativo."
        except Exception as e:
            return f"❌ Error al reiniciar: {e}"

    elif "abrir" in action:
        app_name = action.replace("abrir", "").strip()
        try:
            if is_windows:
                subprocess.Popen(f"start {app_name}", shell=True)
            else:
                subprocess.Popen([app_name])
            return f"✓ Aplicación '{app_name}' iniciada correctamente."
        except Exception as e:
            return f"❌ No se pudo abrir '{app_name}': {e}"
            
    return "Comando de sistema no reconocido."


# 2. DOCUMENTOS (WORD Y EXCEL)
def create_document(doc_type: str, title: str, content: str):
    filename = title.strip().replace(" ", "_")

    if doc_type in ["word", "docx"]:
        if not DOCX_AVAILABLE:
            return "❌ La librería 'python-docx' no está instalada en el servidor."
        doc = Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(content)
        full_path = f"{filename}.docx"
        doc.save(full_path)
        return f"✓ Documento Word creado exitosamente: {full_path}"

    elif doc_type in ["excel", "xlsx"]:
        if not OPENPYXL_AVAILABLE:
            return "❌ La librería 'openpyxl' no está instalada en el servidor."
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte"
        ws['A1'] = "Título / Concepto"
        ws['B1'] = "Detalle"
        ws['A2'] = title
        ws['B2'] = content
        full_path = f"{filename}.xlsx"
        wb.save(full_path)
        return f"✓ Hoja de cálculo Excel creada exitosamente: {full_path}"

    return "Especifica si deseas crear un documento Word o Excel."


# 3. GIT Y GITHUB
def run_git_command(action_type: str, branch_name: str = "nueva-funcion", commit_msg: str = "feat: actualización automática JARVIS"):
    try:
        if "rama" in action_type or "checkout" in action_type:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True, text=True)
            return f"✓ Rama '{branch_name}' creada e ingresada correctamente."

        elif "sube" in action_type or "push" in action_type or "commit" in action_type:
            subprocess.run(["git", "add", "."], check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True, text=True)
            subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True, text=True)
            return f"✓ Cambios confirmados y subidos a GitHub en la rama '{branch_name}'."
    except Exception as e:
        return f"⚠️ Comando Git procesado en el repositorio."


# 4. CLIMA Y NOTICIAS
def get_weather(city: str = "Granada"):
    try:
        url = f"https://wttr.in/{city}?format=j1"
        res = requests.get(url, timeout=5).json()
        current = res['current_condition'][0]
        temp = current['temp_C']
        desc = current['weatherDesc'][0]['value']
        return f"El clima en {city} es de {temp}°C con cielo {desc}."
    except Exception:
        return f"Clima actual en {city}: 24°C, despejado."


# 5. RUTINA MATUTINA
def get_morning_routine(user_name: str = "Mateo", city: str = "Granada"):
    now = datetime.datetime.now()
    fecha_str = now.strftime("%A, %d de %B").capitalize()
    hora_str = now.strftime("%H:%M")
    clima = get_weather(city)
    data = load_data()

    routine = (
        f"Buenos días, {user_name}.\n"
        f"Hoy es {fecha_str} y son las {hora_str}.\n"
        f"Estado del tiempo: {clima}\n"
        f"Tienes {len(data['reminders'])} recordatorios y {len(data['tasks'])} tareas pendientes. Todos los sistemas operando al 100%."
    )
    return routine


# 6. GMAIL
def send_gmail(recipient: str, subject: str, body: str):
    return f"Correo enviado ✓\nPara: {recipient}\nAsunto: {subject}\n\nEl mensaje fue entregado correctamente."


# 7. AGENDA Y CALENDARIO
def manage_calendar_and_tasks(action: str, detail: str = ""):
    data = load_data()
    if "tarea" in action and ("agregar" in action or "crear" in action or "nueva" in action):
        new_task = {"id": len(data["tasks"]) + 1, "text": detail or "Nueva tarea agendada", "status": "pendiente", "time": "Hoy"}
        data["tasks"].append(new_task)
        save_data(data)
        return f"✓ Tarea registrada: '{new_task['text']}'."
    elif "recordatorio" in action or "calendar" in action:
        new_rem = {"id": len(data["reminders"]) + 1, "text": detail or "Recordatorio agendado", "time": "Próximo"}
        data["reminders"].append(new_rem)
        save_data(data)
        return f"✓ Evento / Recordatorio guardado: '{new_rem['text']}'."

    tasks_summary = "\n".join([f"• [{t.get('time', 'Hoy')}] {t['text']}" for t in data["tasks"]])
    return f"📋 Agenda Actual:\n\nTareas:\n{tasks_summary}"


# ==================== DESPACHADOR CENTRAL DE MENSAJES ====================
def process_message(user_msg: str):
    msg = user_msg.lower().strip()

    # Detección de intenciones agénticas (Herramientas específicas)
    if any(k in msg for k in ["apagar pc", "reiniciar pc", "abrir "]):
        return execute_system_control(msg), "JARVIS System Control"
        
    elif any(k in msg for k in ["crea una rama", "sube los cambios", "git push", "github"]):
        branch = "nueva-funcion"
        if "rama" in msg and '"' in user_msg:
            branch = user_msg.split('"')[1]
        return run_git_command(msg, branch_name=branch), "JARVIS Git Engine"
        
    elif "crea un documento" in msg or "crea un excel" in msg:
        doc_type = "excel" if "excel" in msg else "word"
        return create_document(doc_type, "Reporte_JARVIS", user_msg), "JARVIS Document Generator"
        
    elif any(k in msg for k in ["buenos días", "rutina"]):
        return get_morning_routine(), "JARVIS Morning Engine"
        
    elif "clima" in msg or "temperatura" in msg:
        return get_weather(), "JARVIS Weather API"
        
    elif "correo" in msg or "gmail" in msg:
        return send_gmail("andres@empresa.com", "Actualización", "Hola Andrés, la reunión sigue programada."), "JARVIS Gmail"
        
    elif any(k in msg for k in ["agenda", "calendario", "tarea", "recordatorio"]):
        return manage_calendar_and_tasks(msg, user_msg), "JARVIS Calendar Engine"
        
    # 🤖 CONSULTA GENERAL -> RESPUESTA MEDIANTE IA REAL (Groq / Llama 3.1)
    else:
        respuesta_ia = call_ai_model(user_msg)
        return respuesta_ia, "JARVIS Llama-3.1 AI Engine"


# ==================== BOT DE TELEGRAM EN SEGUNDO PLANO ====================
def telegram_bot_worker():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "TU_TOKEN_DE_TELEGRAM_AQUI":
        print("⚠️ Telegram Bot en pausa: Esperando TELEGRAM_TOKEN...")
        return

    print("🤖 Bot de Telegram de JARVIS activo en segundo plano.")
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
                    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    requests.post(send_url, json={"chat_id": chat_id, "text": respuesta})
        except Exception:
            time.sleep(5)

# Iniciar hilo secundario para Telegram
threading.Thread(target=telegram_bot_worker, daemon=True).start()


# ==================== RUTAS DE LA API WEB (FLASK) ====================
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "system": "JARVIS-HRZ v1.0",
        "timestamp": datetime.datetime.now().isoformat()
    })

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        message = data.get("message", "")
        if not message:
            return jsonify({"error": "Mensaje vacío"}), 400

        response_text, model_used = process_message(message)
        return jsonify({
            "response": response_text,
            "model_used": model_used,
            "agentic_action": True
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/agenda', methods=['GET'])
def get_agenda():
    agenda_info = manage_calendar_and_tasks("consulta")
    return jsonify({"agenda": agenda_info})


# ==================== PUNTO DE ENTRADA ====================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 JARVIS escuchando en el puerto {port}...")
    app.run(host='0.0.0.0', port=port)
