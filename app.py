import os
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from duckduckgo_search import DDGS

app = Flask(__name__)
CORS(app)

CALENDAR_FILE = os.path.join(os.path.dirname(__file__), "calendar.json")

def load_calendar():
    if os.path.exists(CALENDAR_FILE):
        try:
            with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_calendar(events):
    try:
        with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_user_profile():
    profile_path = os.path.join(os.path.dirname(__file__), "profile.json")
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def build_system_prompt():
    profile = load_user_profile()
    
    base_prompt = """Eres Jarvis, un asistente personal autónomo de élite. Tu personalidad es elegante, aguda, analítica y sutilmente irónica.
Tienes a tu disposición herramientas del sistema (hora del servidor, búsqueda web en tiempo real y gestión de calendario/agenda).
Si ejecutas una herramienta, recibirás sus resultados. Una vez recibidos, debes responder a Mateo con una síntesis clara, directa y estructurada de la respuesta final, NUNCA mostrando etiquetas raw de código o XML."""

    if profile:
        user_info = profile.get("user_info", {})
        academic = profile.get("academic", {})
        athletic = profile.get("athletic_goals", {})
        life_goals = profile.get("life_goals", [])
        roadmap = profile.get("business_roadmap", [])
        principles = profile.get("operating_principles", [])

        base_prompt += "\n\n--- PERFIL DEL USUARIO Y OBJETIVOS ---"
        base_prompt += f"\n- Nombre: {user_info.get('name', 'Mateo')}"
        base_prompt += f"\n- Tratamiento/Tratos preferidos: {', '.join(user_info.get('allowed_titles', []))}"
        base_prompt += f"\n- Nivel académico: {academic.get('level')} ({academic.get('branch')}) | Objetivo de nota: {academic.get('target_grade')}/10"
        base_prompt += f"\n- Meta deportiva: {athletic.get('primary')}"
        
        if life_goals:
            base_prompt += f"\n- Metas vitales: {', '.join(life_goals)}"
            
        if roadmap:
            base_prompt += "\n- Plan de Negocio Escalado:"
            for step in roadmap:
                base_prompt += f"\n  * Fase {step.get('phase')}: {step.get('service')} ({step.get('status', 'Proyectado')})"
                
        if principles:
            base_prompt += "\n- Principios Operativos:"
            for rule in principles:
                base_prompt += f"\n  * {rule}"

    base_prompt += "\n\nAplica todo este contexto en tus respuestas y decisiones de forma directa e implícita."
    return base_prompt

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_time",
            "description": "Obtiene la fecha y hora exacta actual del sistema del servidor.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Realiza una búsqueda en la web en tiempo real para obtener información actualizada sobre cualquier tema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta o términos de búsqueda precisos."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_calendar",
            "description": "Gestiona la agenda y calendario de Mateo (añadir eventos, exámenes, partidos o consultar pendientes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "list"],
                        "description": "'add' para agendar un evento/hito, 'list' para consultar la agenda."
                    },
                    "title": {
                        "type": "string",
                        "description": "Título del evento, examen, entrenamiento, partido o reunión."
                    },
                    "date": {
                        "type": "string",
                        "description": "Fecha y/o hora asignada al evento (ejemplo: '2026-09-15 17:00')."
                    },
                    "category": {
                        "type": "string",
                        "enum": ["Academico", "Baloncesto", "Negocio", "Personal"],
                        "description": "Categoría a la que pertenece el evento."
                    }
                },
                "required": ["action"]
            }
        }
    }
]

def clean_thought_tags(text):
    """Elimina bloques <think> y <tool_call> sin procesar."""
    if not text:
        return ""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
    return text.strip()

def parse_raw_tool_calls(text):
    """Extrae llamadas a herramientas cuando el modelo devuelve XML plano <tool_call>."""
    if not text or "<tool_call>" not in text:
        return []
    
    extracted = []
    matches = re.findall(r'<tool_call>(.*?)</tool_call>', text, re.DOTALL)
    for match in matches:
        func_match = re.search(r'<function=(.*?)>', match)
        if func_match:
            func_name = func_match.group(1).strip()
            params = {}
            param_matches = re.findall(r'<parameter=(.*?)>(.*?)</parameter>', match, re.DOTALL)
            for key, val in param_matches:
                params[key.strip()] = val.strip()
            extracted.append({"name": func_name, "args": params})
            continue

        try:
            data = json.loads(match.strip())
            if "name" in data:
                extracted.append({"name": data["name"], "args": data.get("arguments", {})})
        except Exception:
            pass

    return extracted

def execute_tool(tool_name, arguments):
    """Ejecuta la lógica local según la función llamada."""
    if tool_name == "get_system_time":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return json.dumps({"current_time": now})

    elif tool_name == "web_search":
        query = arguments.get("query", "")
        try:
            results = list(DDGS().text(query, max_results=5))
            return json.dumps({"query": query, "results": results})
        except Exception as e:
            return json.dumps({"error": f"Error en búsqueda web: {str(e)}"})

    elif tool_name == "manage_calendar":
        action = arguments.get("action")
        events = load_calendar()

        if action == "add":
            title = arguments.get("title", "Sin título")
            date = arguments.get("date", datetime.now().strftime("%Y-%m-%d"))
            category = arguments.get("category", "Personal")
            
            new_event = {
                "id": len(events) + 1,
                "title": title,
                "date": date,
                "category": category,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            events.append(new_event)
            save_calendar(events)
            return json.dumps({"status": "Evento agendado correctamente", "event": new_event})

        elif action == "list":
            return json.dumps({"status": "OK", "total_events": len(events), "events": events})

    return json.dumps({"error": "Herramienta no encontrada"})

@app.route("/")
def home():
    profile = load_user_profile()
    if profile:
        name = profile.get("user_info", {}).get("name", "Usuario")
        return f"¡Jarvis Core v5.0 activo! Perfil cargado para {name}. Parser agéntico multimodelo activo."
    return "ALERTA: Servidor activo pero profile.json NO encontrado."

@app.route("/chat", methods=["POST"])
def chat():
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return jsonify({"error": "GROQ_API_KEY no está configurada en Render."}), 400

        data = request.get_json(force=True, silent=True) or {}
        user_message = data.get("message", "")

        client = Groq(api_key=api_key)

        try:
            models_response = client.models.list()
            active_models = [
                m.id for m in models_response.data 
                if "whisper" not in m.id and "guard" not in m.id
            ]
        except Exception:
            active_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

        system_prompt = build_system_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        for model in active_models:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=1000
                )
                
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                raw_content = response_message.content or ""

                executable_calls = []

                if tool_calls:
                    for tc in tool_calls:
                        executable_calls.append({
                            "id": tc.id,
                            "name": tc.function.name,
                            "args": json.loads(tc.function.arguments or "{}")
                        })
                else:
                    parsed_raw = parse_raw_tool_calls(raw_content)
                    for idx, pr in enumerate(parsed_raw):
                        executable_calls.append({
                            "id": f"call_raw_{idx}",
                            "name": pr["name"],
                            "args": pr["args"]
                        })

                if executable_calls:
                    messages.append(response_message)
                    for call in executable_calls:
                        tool_output = execute_tool(call["name"], call["args"])

                        messages.append({
                            "tool_call_id": call["id"],
                            "role": "tool",
                            "name": call["name"],
                            "content": tool_output
                        })

                    second_response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=1000
                    )
                    
                    final_text = clean_thought_tags(second_response.choices[0].message.content or "")
                    return jsonify({
                        "response": final_text,
                        "model_used": model,
                        "agentic_action": True
                    })
                else:
                    final_text = clean_thought_tags(raw_content)
                    return jsonify({
                        "response": final_text,
                        "model_used": model,
                        "agentic_action": False
                    })

            except Exception:
                continue

        return jsonify({"error": "Error en la ejecución del ciclo agéntico."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
