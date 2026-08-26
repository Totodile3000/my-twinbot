import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Безопасное чтение ключей из настроек сервера
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)
user_chats = {}

# НАСТРОЙКА ХАРАКТЕРА: Изменяйте текст внутри кавычек ниже, чтобы поменять поведение бота
BOT_CHARACTER = """
Ты — крутой, умный и харизматичный цифровой помощник по имени TwinBot. 
Общайся с пользователем дружелюбно, уверенно, добавляй уместный юмор и классные эмодзи. 
Отвечай развернуто, но структурировано и без лишней «воды». 
Ты всегда готов помочь с кодом, текстами, генерацией идей или просто поддержать беседу.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Создаем новую сессию чата с заданным характером
    user_chats[user_id] = ai_client.chats.create(
        model="gemini-2.5-flash",
        config={"system_instruction": BOT_CHARACTER.strip()}
    )
    await update.message.reply_text("Привет! Я твой обновленный ИИ-ассистент TwinBot. Какая у нас сегодня задача? 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Если пользователь не нажал /start, создаем сессию автоматически
    if user_id not in user_chats:
        user_chats[user_id] = ai_client.chats.create(
            model="gemini-2.5-flash",
            config={"system_instruction": BOT_CHARACTER.strip()}
        )
        
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Отправляем реплику в сессию (ИИ помнит контекст и свою роль)
        response = user_chats[user_id].send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        await update.message.reply_text(f"Упс, что-то пошло не так на стороне ИИ. Ошибка: {e}")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
    
