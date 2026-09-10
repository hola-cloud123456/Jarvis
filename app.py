import os
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app)

def load_user_profile():
    """Carga el perfil de usuario y contexto de negocio desde profile.json."""
    profile_path = os.path.join(os.path.dirname(__file__), "profile.json")
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def build_system_prompt():
    """Construye el Prompt del Sistema inyectando el perfil del negocio."""
    profile = load_user_profile()
    
    base_prompt = """Eres Jarvis, un asistente personal autónomo de élite. Tu personalidad es elegante, aguda, analítica y sutilmente irónica.
Tienes a tu disposición herramientas del sistema. Si necesitas ejecutar una acción interna o consultar el estado, usa tus herramientas antes de responder."""

    if profile:
        base_prompt += f"\n\n--- CONTEXTO DEL USUARIO Y NEGOCIO ---"
        base_prompt += f"\n- Usuario: {profile.get('user_name', 'Usuario')}"
        base_prompt += f"\n- Rol: {profile.get('role', 'No especificado')}"
        base_prompt += f"\n- Resumen del negocio/actividad: {profile.get('business_summary', 'No especificado')}"
        
        projects = profile.get("active_projects", [])
        if projects:
            base_prompt += "\n- Proyectos Activos:"
            for p in projects:
                base_prompt += f"\n  * {p.get('name')}: {p.get('status')} | Objetivo: {p.get('goal')}"
                
        principles = profile.get("operating_principles", [])
        if principles:
            base_prompt += "\n- Reglas de Operación Técnicas:"
            for rule in principles:
                base_prompt += f"\n  * {rule}"

    base_prompt += "\n\nAplica este contexto en todas tus decisiones y sugerencias de forma implícita."
    return base_prompt

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_time",
            "description": "Obtiene la fecha y hora exacta actual del sistema del servidor.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

def clean_thought_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def execute_tool(tool_name, arguments):
    if tool_name == "get_system_time":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return json.dumps({"current_time": now})
    return json.dumps({"error": "Herramienta no encontrada"})

@app.route("/")
def home():
    return "¡Jarvis Agent Core v4.0 con Perfil de Negocio Activo!"

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

        # Generar prompt dinámico con los datos de profile.json
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

                if tool_calls:
                    messages.append(response_message)
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments or "{}")
                        tool_output = execute_tool(function_name, function_args)

                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
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
                    final_text = clean_thought_tags(response_message.content or "")
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
