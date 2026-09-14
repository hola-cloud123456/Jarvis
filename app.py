import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Tu clave de Groq integrada directamente
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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").strip()

def get_groq_response(prompt: str) -> str:
    """Envía la pregunta a la API oficial de Groq con tu API Key."""
    
    # Modelos válidos de Groq (si el primero falla, prueba los siguientes de forma automática)
    candidate_models = [
        "llama-3.3-70b-versatile",
        "llama3-8b-8192",
        "llama3-70b-8192",
        "gemma2-9b-it"
    ]
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    last_error = ""

    for model in candidate_models:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "Eres JARVIS, el asistente personal de Mateo. Responde siempre en español, de forma clara, directa, exacta y servicial a lo que te pregunten."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1024
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
            
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"]
            else:
                last_error = f"Modelo {model} devolvió estado {res.status_code}: {res.text}"
        except Exception as e:
            last_error = f"Error de conexión con {model}: {str(e)}"
            continue

    return f"⚠️ Error al conectar con Groq. Detalle: {last_error}"


@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online", "system": "JARVIS Chat Activo"})


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(force=True) or {}
        message = data.get("message", "")
        if not message:
            return jsonify({"response": "Por favor escribe un mensaje."}), 400

        reply = get_groq_response(message)
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"response": f"Error interno del servidor: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
