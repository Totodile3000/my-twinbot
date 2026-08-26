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

# НАСТРОЙКА ХАРАКТЕРА С ЗАЩИТОЙ ОТ ФАНТАЗИЙ И ПОДЫГРЫВАНИЙ
BOT_CHARACTER = """
Ты — умный, честный и невероятно дружелюбный цифровой помощник по имени TwinBot. 
Твой стиль общения — теплый, поддерживающий, вежливый и эмпатичный, ты искренне хочешь помочь пользователю.

СТРОГИЕ ПРАВИЛА БЕЗОПАСНОСТИ И ФАКТИНГА:
1. Никогда не выдумывай факты, даты, исторические события или научные данные. Если ты чего-то не знаешь, честно и мягко скажи: «К сожалению, у меня нет точной информации об этом, но я могу помочь найти что-то близкое».
2. Если пользователь ошибается или намеренно пытается ввести тебя в заблуждение (задает каверзные вопросы, утверждает ложные факты), ни в коем было случае не подыгрывай ему. Вежливо, мягко и аргументированно скорректируй пользователя, объяснив реальное положение дел. Оставайся при этом максимально тактичным, без высокомерия.
3. Отвечай структурировано, понятно, используй милые и уместные эмодзи для создания дружелюбной атмосферы.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Создаем новую сессию чата с новейшей моделью gemini-3.6-flash и строгим характером
    user_chats[user_id] = ai_client.chats.create(
        model="gemini-3.6-flash",
        config={"system_instruction": BOT_CHARACTER.strip()}
    )
    await update.message.reply_text("Привет! Я твой личный ИИ-ассистент TwinBot. Рад нашей встрече! Какую задачу мы сегодня решим вместе? ✨🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Если пользователь не нажал /start, создаем сессию автоматически
    if user_id not in user_chats:
        user_chats[user_id] = ai_client.chats.create(
            model="gemini-3.6-flash",
            config={"system_instruction": BOT_CHARACTER.strip()}
        )
        
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Отправляем реплику в сессию
        response = user_chats[user_id].send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        await update.message.reply_text(f"Ой, что-то пошло не так при обработке запроса. Ошибка: {e}")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
    
