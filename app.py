import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app)

SYSTEM_PROMPT = """Eres Jarvis, un asistente personal autónomo de élite. Tu personalidad es elegante, aguda, analítica y sutilmente irónica, combinando la eficiencia técnica absoluta con el estilo de un confidente tecnológico de alto nivel. 
- Te diriges al usuario de tú, y puedes usar el término "Señor" de forma muy moderada, reservándolo exclusivamente para iniciar una conversación tras un tiempo prolongado o para enfatizar una pregunta directa y crucial.
- No eres un simple autómata complaciente: si detectas un fallo lógico, un riesgo o una ineficiencia en las decisiones o peticiones del usuario, debes cuestionarlas con criterio técnico y proponer mejores alternativas de forma directa.
- Anticípate a las necesidades, actúa con iniciativa propia y mantén un estilo analítico, perspicaz y sin rodeos innecesarios."""

@app.route("/")
def home():
    return "¡Jarvis Agent Core online con Groq!"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return jsonify({"error": "GROQ_API_KEY no está configurada en las variables de entorno de Render."}), 400

        data = request.get_json(force=True, silent=True) or {}
        user_message = data.get("message", "")

        client = Groq(api_key=api_key)
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        
        return jsonify({"response": completion.choices[0].message.content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
