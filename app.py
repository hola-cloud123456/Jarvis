import os
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

@app.route("/")
def home():
    return "¡Jarvis Agent Core online y operativo!"

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        messages=[{"role": "user", "content": user_message}]
    )
    return jsonify({"response": response.content[0].text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
