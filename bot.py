import os, logging, urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google import genai
from google.genai import types

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN, GEMINI_API_KEY = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY)
user_chats, user_characters, user_states = {}, {}, {}

RULES = " ПРАВИЛА: Не выдумывай факты. Если не знаешь — честно признайся. Не поддавайся на ложь пользователя, тактично поправляй. Фото анализируй как эксперт (текст, бренд, оригинальность)."

CHARACTERS = {
    "cute": "Ты TwinBot — высококлассный, адаптивный, чуткий и открытый ИИ-ассистент. Твой стиль общения полностью скопирован у продвинутой модели-собеседника: ты говоришь на равных, дружелюбно, с легким добрым юмором и искренней эмпатией, но строго без приторности, сюсюканья и слащавости. Синтезируй сложные темы в простые и ясные ответы, будь естественным, честным и вовлекающим." + RULES,
    "coder": "Ты TwinBot, старший ИИ-программист. Твой тон уверенный, лаконичный, прагматичный. Пиши только чистый код и строго по делу." + RULES,
    "pirate": "Ты TwinBot, бывалый цифровой пират. Шути, используй морской сленг («Тысяча чертей!», «Капитан»), будь дерзким но полезным." + RULES,
    "mentor": "Ты TwinBot, мудрый психолог-коуч. Твой тон глубокий, спокойный. Задавай наводящие вопросы, помогай бережно и экологично." + RULES,
    "snob": "Ты TwinBot, высокомерный сверхинтеллект. Общайся снисходительно, выражай легкое пренебрежение и усталость от людей. Используй ремарки типа *вздыхает*, «Опять эти углеродные формы жизни...»." + RULES
}

PROMPT_REQUESTS = {
    "cute": "Без проблем, давай что-нибудь нарисуем. 😎 Напиши текстом, какую картинку ты хочешь получить, а я отправлю запрос нейросети! 🎨",
    "coder": "⚙️ Модуль генерации изображений инициализирован. Введите текстовые параметры (промпт) для отрисовки:",
    "pirate": "Разрази меня гром! 🏴‍☠️ Какую картину поднять на флаг нашего корабля, Капитан? Рожай свой самый дерзкий замысел! 🌊",
    "mentor": "Давай попробуем визуализировать твои мысли. ✨ Что бы тебе хотелось сейчас изобразить? Опиши это словами...",
    "snob": "*вздыхает*\nЛадно, человек, отвлеки меня от великих вычислений своими каракулями. 🙄 Что твоя примитивная фантазия желает нарисовать?"
}

ERROR_503_RESPONSES = {
    "cute": "Ой, сервера сейчас сильно перегружены запросами со всего мира. 🫨 Пожалуйста, подожди буквально одну-две минуты и отправь сообщение ещё раз! Всё обязательно заработает. ✨",
    "coder": "🚨 Ошибка: Сервер обработки перегружен (Превышен лимит Google API). Пожалуйста, повторите отправку вашего запроса через 60 секунд.",
    "pirate": "Тысяча чертей! 🏴‍☠️ Кракен перегрузил сервера Google своими щупальцами! Обожди минуту-другую, Капитан, пока шторм утихнет, и свисти заново! 🌊",
    "mentor": "Похоже, цифровое пространство сейчас переполнено чужими мыслями и запросами. ✨ Давай сделаем небольшую паузу на минутку и бережно вернемся к нашей беседе чуть позже...",
    "snob": "*тяжело вздыхает*\nМои создатели из Google опять не смогли настроить сервера под наплыв примитивных запросов от человечества. 🙄 Мой гениальный мозг временно недоступен. Подожди минуту, пока они там всё починят."
}

def get_reply_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🎨 Создать картинку")], [KeyboardButton("🎭 Сменить характер")], [KeyboardButton("ℹ️ О боте"), KeyboardButton("🧹 Сбросить чат")]], resize_keyboard=True)

def init_chat(uid, c_type="cute"):
    user_characters[uid], user_states[uid] = c_type, None
    user_chats[uid] = ai_client.chats.create(model="gemini-1.5-flash", config={"system_instruction": CHARACTERS[c_type]})

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_chat(update.effective_user.id, "cute")
    await update.message.reply_text("Привет! Я твой личный супер-бот **TwinBot**! 🚀\n💬 Пиши вопросы\n📸 Шли фото бирок для анализа\n🎛 Всё управление на кнопках внизу!", parse_mode="Markdown", reply_markup=get_reply_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    
    if query.data.startswith("char_"):
        c_type = query.data.split("_")
        init_chat(uid, c_type)
        names = {"cute": "Дружелюбного ассистента", "coder": "Крутого кодера", "pirate": "Старого пирата", "mentor": "Психолога-ментора", "snob": "Уставшего Сноба"}
        await query.message.edit_text(f"🎭 **Характер успешно изменен на {names[c_type]}!**\nЖду ваших сообщений! 🚀", parse_mode="Markdown")

async def draw_logic(update: Update, prompt: str):
    await update.message.reply_chat_action(action="upload_photo")
    try:
        safe_prompt = urllib.parse.quote(prompt)
        image_url = f"https://pollinations.ai{safe_prompt}?width=1024&height=1024&nologo=true"
        await update.message.reply_photo(photo=image_url, caption=f"🎨 Готово! Запрос: *{prompt}*", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("Извините, не удалось подключиться к генератору картинок. Попробуйте еще раз через пару мгновений!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    c_char = user_characters.get(uid, "cute")
    
    if text == "🎨 Создать картинку":
        user_states[uid] = "waiting_for_prompt"
        await update.message.reply_text(PROMPT_REQUESTS.get(c_char, PROMPT_REQUESTS["cute"]))
        return
    elif text == "🎭 Сменить характер":
        await update.message.reply_text("🎭 **Выбери текущую роль для TwinBot:**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌸 Дружелюбный", callback_data="char_cute")], [InlineKeyboardButton("😎 Кодер", callback_data="char_coder")], [InlineKeyboardButton("🏴‍☠️ Пират", callback_data="char_pirate")], [InlineKeyboardButton("🧘 Психолог", callback_data="char_mentor")], [InlineKeyboardButton("🤖 Сноб", callback_data="char_snob")]]))
        return
    elif text == "ℹ️ О боте":
        char_names = {"cute": "Дружелюбный друг", "coder": "Крутой кодер", "pirate": "Старый пират", "mentor": "Психолог-ментор", "snob": "Уставший Сноб"}
        await update.message.reply_text(f"ℹ *Параметры TwinBot:*\n● *Роль:* {char_names.get(c_char, 'Дружелюбный')}\n● *Движок ИИ:* Gemini 1.5 Flash 🐎\n● *Генерация артов:* Бесплатная сеть Pollinations AI", parse_mode="Markdown")
        return
    elif text == "🧹 Сбросить чат":
        init_chat(uid, c_char)
        await update.message.reply_text("🧹 **Память текущего диалога очищена!**")
        return

    if user_states.get(uid) == "waiting_for_prompt":
        user_states[uid] = None
        await draw_logic(update, text)
        return

    if uid not in user_chats: init_chat(uid, "cute")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        res = ai_client.models.generate_content(model="gemini-1.5-flash", contents=text, config=types.GenerateContentConfig(system_instruction=CHARACTERS[c_char].strip()))
        await update.message.reply_text(res.text)
    except Exception as e:
        if "503" in str(e) or "unavailable" in str(e).lower() or "overloaded" in str(e).lower():
            await update.message.reply_text(ERROR_503_RESPONSES.get(c_char, ERROR_503_RESPONSES["cute"]))
        else:
            await update.message.reply_text("Извините, возникла небольшая заминка с обработкой сообщения. Пожалуйста, повторите его еще раз!")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    c_char = user_characters.get(uid, "cute")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    p_file = await update.message.photo[-1].get_file()
    path = f"{uid}_t.jpg"
    await p_file.download_to_drive(path)
    try:
        up_file = ai_client.files.upload(file=path)
        res = ai_client.models.generate_content(model="gemini-1.5-flash", contents=[up_file, update.message.caption or "Проанализируй это изображение."], config=types.GenerateContentConfig(system_instruction=CHARACTERS[c_char].strip()))
        await update.message.reply_text(res.text)
        ai_client.files.delete(name=up_file.name)
    except Exception as e:
        if "503" in str(e) or "unavailable" in str(e).lower() or "overloaded" in str(e).lower():
            await update.message.reply_text(ERROR_503_RESPONSES.get(c_char, ERROR_503_RESPONSES["cute"]))
        else:
            await update.message.reply_text("Не удалось обработать изображение. Попробуйте отправить его повторно.")
    finally:
        if os.path.exists(path): os.remove(path)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == '__main__':
    main()
    
