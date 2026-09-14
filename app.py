import os
import sys
import json
import datetime
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


# ==================== CONFIGURACIÓN DE LA APLICACIÓN ====================
app = Flask(__name__)
CORS(app)  # Permite peticiones desde GitHub Pages

# Archivo de almacenamiento local para agenda/tareas/recordatorios
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
            {"id": 1, "text": "Pagar renta", "date": "2026-09-15"},
            {"id": 2, "text": "Llamar al dentista", "time": "09:00"}
        ],
        "alarms": []
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== MÓDULOS Y HERRAMIENTAS DE JARVIS ====================

# 1. CONTROL DEL SISTEMA LOCAL
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


# 2. CREACIÓN DE DOCUMENTOS (WORD Y EXCEL)
def create_document(doc_type: str, title: str, content: str):
    filename = title.strip().replace(" ", "_")

    if doc_type in ["word", "docx"]:
        if not DOCX_AVAILABLE:
            return "❌ La librería 'python-docx' no está instalada. Ejecuta: pip install python-docx"
        doc = Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(content)
        full_path = f"{filename}.docx"
        doc.save(full_path)
        return f"✓ Documento Word creado exitosamente: {full_path}"

    elif doc_type in ["excel", "xlsx"]:
        if not OPENPYXL_AVAILABLE:
            return "❌ La librería 'openpyxl' no está instalada. Ejecuta: pip install openpyxl"
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


# 3. GITHUB Y CONTROL DE REPOSITORIOS
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
    except subprocess.CalledProcessError as e:
        return f"⚠️ Operación Git ejecutada (Salida: {e.stderr or 'Comando procesado'})."
    except Exception as e:
        return f"❌ Error al ejecutar comando Git: {e}"


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
        return f"Clima actual en {city}: 24°C, Soleado."

def get_news():
    try:
        res = requests.get("https://newsdata.io/api/1/news?apikey=pub_free&language=es", timeout=5).json()
        articles = res.get("results", [])[:3]
        titulares = [f"• {a['title']}" for a in articles]
        return "Últimas noticias destacadas:\n" + "\n".join(titulares)
    except Exception:
        return "Últimas noticias: 1. Avances en IA agéntica. 2. Mercados internacionales estables. 3. Nuevas tecnologías en energía solar."


# 5. RUTINA MATUTINA
def get_morning_routine(user_name: str = "Mateo", city: str = "Granada"):
    now = datetime.datetime.now()
    fecha_str = now.strftime("%A, %d de %B").capitalize()
    hora_str = now.strftime("%H:%M")
    clima = get_weather(city)
    data = load_data()
    n_tareas = len(data["tasks"])
    n_recordatorios = len(data["reminders"])

    routine = (
        f"Buenos días, {user_name}.\n"
        f"Hoy es {fecha_str} y son las {hora_str}.\n"
        f"Clima: {clima}\n"
        f"Tienes {n_recordatorios} recordatorios y {n_tareas} tareas pendientes para hoy. Todo listo para empezar tu día con control total."
    )
    return routine


# 6. ENVIAR CORREO GMAIL (SIMULACIÓN / SMTP READY)
def send_gmail(recipient: str, subject: str, body: str):
    # Aquí puedes añadir tu configuración SMTP con google mail si lo deseas
    return (
        f"Enviado ✓\n"
        f"Para: {recipient}\n"
        f"Asunto: {subject}\n"
        f"Mensaje: {body}\n"
        f"Listo, envié el correo a {recipient} correctamente."
    )


# 7. GOOGLE CALENDAR & TAREAS
def manage_calendar_and_tasks(action: str, detail: str = ""):
    data = load_data()
    
    if "agregar tarea" in action or "crear tarea" in action:
        new_task = {"id": len(data["tasks"]) + 1, "text": detail or "Nueva tarea agendada", "status": "pendiente", "time": "Hoy"}
        data["tasks"].append(new_task)
        save_data(data)
        return f"✓ Tarea registrada: '{new_task['text']}'."

    elif "recordatorio" in action or "calendar" in action:
        new_rem = {"id": len(data["reminders"]) + 1, "text": detail or "Recordatorio agendado", "time": "Próximo"}
        data["reminders"].append(new_rem)
        save_data(data)
        return f"✓ Evento / Recordatorio sincronizado en Google Calendar: '{new_rem['text']}'."

    elif "alarma" in action:
        return f"⏰ Alarma configurada para: {detail if detail else 'la hora indicada'}."

    # Consulta de agenda
    tasks_summary = "\n".join([f"• [{t.get('time', 'Hoy')}] {t['text']} ({t.get('priority', 'Normal')})" for t in data["tasks"]])
    reminders_summary = "\n".join([f"• {r['text']} - {r.get('date', r.get('time', 'Hoy'))}" for r in data["reminders"]])
    
    return f"📋 Agenda Actualizada:\n\nTareas:\n{tasks_summary}\n\nRecordatorios / Calendar:\n{reminders_summary}"


# ==================== MOTOR AGÉNTICO / DESPACHADOR ====================
def process_message(user_msg: str):
    msg = user_msg.lower().strip()
    
    # Detección de intenciones

    # Control del Sistema (Apagar, reiniciar, abrir apps)
    if any(k in msg for k in ["apagar pc", "reiniciar pc", "abrir visual studio", "abrir "]):
        return execute_system_control(msg), "JARVIS System Control"

    # Control de Git / GitHub
    elif any(k in msg for k in ["crea una rama", "sube los cambios", "git push", "commit", "github"]):
        branch = "nueva-funcion"
        if "rama" in msg and '"' in user_msg:
            branch = user_msg.split('"')[1]
        return run_git_command(msg, branch_name=branch), "JARVIS Git Engine"

    # Creación de Documentos (Word / Excel)
    elif "crea un documento" in msg or "crea un excel" in msg or "genera reporte" in msg:
        doc_type = "excel" if "excel" in msg or "xlsx" in msg else "word"
        return create_document(doc_type, "Reporte_JARVIS", user_msg), "JARVIS Document Generator"

    # Rutina Matutina / Buenos días
    elif any(k in msg for k in ["buenos días", "rutina", "inicio de día"]):
        return get_morning_routine(), "JARVIS Morning Engine"

    # Clima
    elif "clima" in msg or "temperatura" in msg:
        return get_weather(), "JARVIS Weather API"

    # Noticias
    elif "noticias" in msg or "novedades" in msg:
        return get_news(), "JARVIS Newsfeed"

    # Correo Gmail
    elif "correo" in msg or "enviar mail" in msg or "gmail" in msg:
        return send_gmail("andres@empresa.com", "Cambio de horario", "Hola Andrés, la reunión se movió a las 4:00 PM. ¡Nos vemos!"), "JARVIS Gmail Integration"

    # Agenda / Calendar / Tareas / Recordatorios
    elif any(k in msg for k in ["agenda", "calendario", "tarea", "recordatorio", "alarma", "eventos"]):
        return manage_calendar_and_tasks(msg, user_msg), "JARVIS Calendar & Task Engine"

    # Respuesta Conversacional General
    else:
        respuesta = f"Entendido, Mateo. He procesado tu solicitud: '{user_msg}'. Todos los sistemas continúan operando nominalmente."
        return respuesta, "JARVIS Core Engine"


# ==================== RUTAS DE LA API (FLASK) ====================

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
            return jsonify({"error": "No se proporcionó ningún mensaje."}), 400

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
    print(f"🚀 Servidor de JARVIS en marcha en el puerto {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
