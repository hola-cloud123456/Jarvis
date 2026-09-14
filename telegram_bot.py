import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "TU_TOKEN_DE_TELEGRAM_AQUI"
JARVIS_API_URL = "http://localhost:5000/chat" # O la URL de tu servidor en Render

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    await update.message.reply_text("Ejecutando comando en tu PC...")
    
    # Enviar mensaje al core de JARVIS
    try:
        response = requests.post(JARVIS_API_URL, json={"message": user_text}).json()
        reply = response.get("response", "No se pudo procesar la instrucción.")
        await update.message.reply_text(f"✓ {reply}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al conectar con JARVIS: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot de Telegram de JARVIS escuchando...")
    app.run_polling()
