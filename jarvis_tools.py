import os
import subprocess
import requests
import datetime
import psutil
from docx import Document
from openpyxl import Workbook

# ==================== 1. CONTROL DEL SISTEMA ====================
def system_control(action: str):
    """Apaga, reinicia o abre aplicaciones en el sistema local."""
    action = action.lower()
    if "apagar" in action:
        # En Windows: shutdown /s /t 1 | En Linux/Mac: shutdown -h now
        os.system("shutdown /s /t 5" if os.name == 'nt' else "shutdown -h now")
        return "Iniciando secuencia de apagado en 5 segundos."
    elif "reiniciar" in action:
        os.system("shutdown /r /t 5" if os.name == 'nt' else "reboot")
        return "Iniciando reinicio del sistema."
    elif "abrir" in action:
        app_name = action.replace("abrir", "").strip()
        if os.name == 'nt':
            subprocess.Popen(f"start {app_name}", shell=True)
        else:
            subprocess.Popen([app_name])
        return f"Ejecutando la apertura de {app_name}."
    return "Acción del sistema no reconocida."

# ==================== 2. CREACIÓN DE DOCUMENTOS ====================
def create_document(doc_type: str, title: str, content: str):
    """Crea documentos de Word o Excel automáticamente."""
    filename = f"{title.replace(' ', '_')}"
    
    if doc_type.lower() in ["word", "docx"]:
        doc = Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(content)
        full_path = f"{filename}.docx"
        doc.save(full_path)
        return f"Documento Word creado correctamente: {full_path}"
        
    elif doc_type.lower() in ["excel", "xlsx"]:
        wb = Workbook()
        ws = wb.active
        ws.title = "Datos"
        ws['A1'] = title
        ws['A2'] = content
        full_path = f"{filename}.xlsx"
        wb.save(full_path)
        return f"Hoja de cálculo Excel creada: {full_path}"
        
    return "Tipo de documento no soportado (usa Word o Excel)."

# ==================== 3. CONTROL DE GIT Y GITHUB ====================
def run_git_command(command_type: str, branch_name: str = "main", commit_message: str = "Actualización JARVIS"):
    """Ejecuta comandos de Git directamente en el repositorio."""
    try:
        if command_type == "create_branch":
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            return f"✓ Rama '{branch_name}' creada exitosamente."
        elif command_type == "push":
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push", "origin", branch_name], check=True)
            return f"✓ Cambios subidos a GitHub en la rama '{branch_name}'."
    except Exception as e:
        return f"❌ Error ejecutando Git: {str(e)}"

# ==================== 4. CLIMA Y NOTICIAS ====================
def get_weather(city: str = "Madrid"):
    """Consulta el clima en tiempo real vía OpenWeather u otra API pública."""
    try:
        # API pública gratuita sin API key para pruebas rápidas
        res = requests.get(f"https://wttr.in/{city}?format=j1").json()
        current = res['current_condition'][0]
        temp = current['temp_C']
        desc = current['lang_es'][0]['value'] if 'lang_es' in current else current['weatherDesc'][0]['value']
        return f"El clima actual en {city} es {desc} con una temperatura de {temp}°C."
    except:
        return f"No se pudo obtener el clima para {city}."

# ==================== 5. RUTINA MATUTINA ====================
def morning_routine(user_name: str = "Mateo", city: str = "Madrid"):
    """Genera el resumen de inicio de día."""
    now = datetime.datetime.now()
    fecha_str = now.strftime("%A, %d de %B de %Y")
    hora_str = now.strftime("%H:%M")
    clima_info = get_weather(city)
    
    resumen = (
        f"Buenos días, {user_name}.\n"
        f"Hoy es {fecha_str} y son las {hora_str}.\n"
        f"Estado del tiempo: {clima_info}\n"
        f"Sistemas en línea y listos para ejecutar tus órdenes."
    )
    return resumen
