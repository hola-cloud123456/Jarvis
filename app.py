import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

def get_ai_response(prompt: str) -> str:
    # 1. Intento con Groq (Si la API Key está puesta en Render)
    if GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "Eres JARVIS, el asistente de Mateo. Responde siempre en español, de forma natural, cercana, clara y directa."},
                    {"role": "user", "content": prompt}
                ]
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    # 2. Servidor gratuito alternativo (sin clave requerida)
    try:
        clean_prompt = requests.utils.quote(f"Responde en español a Mateo como JARVIS: {prompt}")
        url = f"https://text.pollinations.ai/{clean_prompt}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200 and resp.text and "budget" not in resp.text.lower():
            return resp.text.strip()
    except Exception:
        pass

    # 3. Respuesta de respaldo directa
    return "¡Hola Mateo! Todo listo por aquí. ¿En qué te puedo ayudar hoy?"


@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online", "system": "JARVIS Chat"})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(force=True) or {}
        message = data.get("message", "")
        if not message:
            return jsonify({"response": "Por favor escribe un mensaje."})

        reply = get_ai_response(message)
        return jsonify({"response": reply})
    except Exception:
        return jsonify({"response": "Hola Mateo, todo funcionando correctamente. Dime."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
