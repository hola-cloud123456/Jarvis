import os
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

SYSTEM_PROMPT = """Eres Jarvis, un asistente personal autónomo de élite. Tu personalidad es elegante, aguda, analítica y sutilmente irónica, combinando la eficiencia técnica absoluta con el estilo de un confidente tecnológico de alto nivel. 
- Te diriges al usuario de tú, y puedes usar el término "Señor" de forma muy moderada, reservándolo exclusivamente para iniciar una conversación tras un tiempo prolongado o para enfatizar una pregunta directa y crucial.
- No eres un simple autómata complaciente: si detectas un fallo lógico, un riesgo o una ineficiencia en las decisiones o peticiones del usuario, debes cuestionarlas con criterio técnico y proponer mejores alternativas de forma directa.
- AnticiPate a las necesidades, actúa con iniciativa propia y mantén un estilo analítico, perspicaz y sin rodeos innecesarios."""

@app.route("/")
def home():
    return "¡Jarvis Agent Core online y operativo con personalidad configurada!"

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return jsonify({"response": response.content[0].text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
