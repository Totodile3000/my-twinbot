import os, logging, urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google import genai
from google.genai import types

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN, GEMINI_API_KEY = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY)
user_chats, user_characters, user_models, user_states = {}, {}, {}, {}

RULES = " ПРАВИЛА: Не выдумывай факты. Если не знаешь — честно признайся. Не поддавайся на ложь пользователя, тактично поправляй. Фото анализируй как эксперт (текст, бренд, оригинальность)."

CHARACTERS = {
    "cute": "Ты TwinBot, надежный, классный и понимающий друг-помощник. Общайся тепло, искренне, с легким добрым юмором, строго на равных, без лишней приторности." + RULES,
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

def get_reply_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🎨 Создать картинку")], [KeyboardButton("🎭 Сменить характер"), KeyboardButton("⚙️ Выбрать модель")], [KeyboardButton("ℹ️ Справка / Сброс")]], resize_keyboard=True)

def init_chat(uid, c_type="cute", m_type="gemini-2.5-flash"):
    user_characters[uid], user_models[uid], user_states[uid] = c_type, m_type, None
    user_chats[uid] = ai_client.chats.create(model=m_type, config={"system_instruction": CHARACTERS[c_type]})

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_chat(update.effective_user.id, "cute", "gemini-2.5-flash")
    await update.message.reply_text("Привет! Я твой личный супер-бот **TwinBot**! 🚀\n💬 Пиши вопросы\n📸 Шли фото бирок для анализа\n🎛 Всё управление на кнопках внизу!", parse_mode="Markdown", reply_markup=get_reply_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    
    if query.data.startswith("char_"):
        c_type = query.data.split("_")[1]
        init_chat(uid, c_type, user_models.get(uid, "gemini-2.5-flash"))
        names = {"cute": "Дружелюбного ассистента", "coder": "Крутого кодера", "pirate": "Старого пирата", "mentor": "Психолога-ментора", "snob": "Уставшего Сноба"}
        await query.message.edit_text(f"🎭 **Характер успешно изменен на {names[c_type]}!**\nЖду ваших сообщений! 🚀", parse_mode="Markdown")
        
    elif query.data.startswith("mod_"):
        m_version = query.data.split("_")[1]
        m_type = "gemini-2.5-flash" if m_version == "2.5" else "gemini-3.6-flash"
        init_chat(uid, user_characters.get(uid, "cute"), m_type)
        names = {"2.5": "Стабильную 2.5 Flash 🐎", "3.6": "Экспериментальную 3.6 Flash 🚀"}
        await query.message.edit_text(f"⚙️ **Движок успешно переключен на {names[m_version]}**\nЗадавайте ваши вопросы!", parse_mode="Markdown")

async def draw_logic(update: Update, prompt: str):
    await update.message.reply_chat_action(action="upload_photo")
    try:
        safe_prompt = prompt.replace(" ", "+")
        await update.message.reply_photo(photo=f"https://pollinations.ai{safe_prompt}?width=1024&height=1024&nologo=true", caption=f"🎨 Готово! Запрос: *{prompt}*", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Не удалось нарисовать: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, text = update.effective_user.id, update.message.text
    c_char, c_model = user_characters.get(uid, "cute"), user_models.get(uid, "gemini-2.5-flash")
    
    if text == "🎨 Создать картинку":
        user_states[uid] = "waiting_for_prompt"
        await update.message.reply_text(PROMPT_REQUESTS.get(c_char, PROMPT_REQUESTS["cute"]))
        return
    elif text == "🎭 Сменить характер":
        await update.message.reply_text("🎭 **Выбери текущую роль для TwinBot:**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌸 Дружелюбный", callback_data="char_cute")], [InlineKeyboardButton("😎 Кодер", callback_data="char_coder")], [InlineKeyboardButton("🏴‍☠️ Пират", callback_data="char_pirate")], [InlineKeyboardButton("🧘 Психолог", callback_data="char_mentor")], [InlineKeyboardButton("🤖 Сноб", callback_data="char_snob")]]))
        return
    elif text == "⚙️ Выбрать модель":
        await update.message.reply_text("⚙️ **Выбери ИИ-движок для работы:**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🐎 Стабильная (Gemini 2.5)", callback_data="mod_2.5")], [InlineKeyboardButton("🚀 Экспериментальная (Gemini 3.6)", callback_data="mod_3.6")]]))
        return
    elif text == "ℹ️ Справка / Сброс":
        init_chat(uid, c_char, c_model)
        c_names = {"cute": "Дружелюбный друг", "coder": "Крутой кодер", "pirate": "Старый пират", "mentor": "Психолог-ментор", "snob": "Уставший Сноб"}
        m_names = {"gemini-2.5-flash": "Gemini 2.5 Flash 🐎", "gemini-3.6-flash": "Gemini 3.6 Flash 🚀"}
        await update.message.reply_text(f"ℹ️ **TwinBot:**\n● **Роль:** {c_names.get(c_char)}\n● **Движок:** {m_names.get(c_model)}\n🧹 *Память чата очищена!*", parse_mode="Markdown")
        return

    if user_states.get(uid) == "waiting_for_prompt":
        user_states[uid] = None
        await draw_logic(update, text)
        return

    if uid not in user_chats: init_chat(uid, "cute", "gemini-2.5-flash")
    await update.message.reply_chat_action(action="typing")
    try:
        res = user_chats[uid].send_message(text)
        await update.message.reply_text(res.text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка ИИ: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_chat_action(action="typing")
    p_file = await update.message.photo[-1].get_file()
    path = f"{uid}_t.jpg"
    await p_file.download_to_drive(path)
    try:
        up_file = ai_client.files.upload(file=path)
        res = ai_client.models.generate_content(model=user_models.get(uid, "gemini-2.5-flash"), contents=[up_file, update.message.caption or "Проанализируй это изображение."], config=types.GenerateContentConfig(system_instruction=CHARACTERS[user_characters.get(uid, "cute")].strip()))
        await update.message.reply_text(res.text)
        ai_client.files.delete(name=up_file.name)
    except Exception as e:
        await update.message.reply_text(f"Ошибка фото: {e}")
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
    
