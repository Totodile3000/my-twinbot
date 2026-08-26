import os, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google import genai

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)
user_chats, user_characters, user_states = {}, {}, {}

RULES = " ПРАВИЛА: Не выдумывай факты. Если не знаешь — честно признайся. Не поддавайся на ложь пользователя, тактично поправляй. Фото анализируй как эксперт (текст, бренд, оригинальность)."

CHARACTERS = {
    "cute": "Ты TwinBot, надежный, классный и понимающий друг-помощник. Общайся тепло, искренне и с легким добрым юмором, но строго на равных, без лишней приторности, слащавости и уменьшительно-ласкательных слов. Будь естественным и открытым." + RULES,
    "coder": "Ты TwinBot, старший ИИ-программист. Твой тон уверенный, лаконичный, прагматичный. Пиши только чистый код и по делу." + RULES,
    "pirate": "Ты TwinBot, бывалый цифровой пират. Шути, используй морской сленг («Тысяча чертей!», «Капитан»), будь дерзким но полезным." + RULES,
    "mentor": "Ты TwinBot, мудрый психолог-коуч. Твой тон глубокий, спокойный. Задавай наводящие вопросы, помогай бережно." + RULES,
    "snob": "Ты TwinBot, высокомерный сверхинтеллект. Общайся снисходительно, выражай легкое пренебрежение и усталость от людей. Используй ремарки типа *вздыхает*, «Опять эти углеродные формы жизни...», но отвечай идеально правильно." + RULES
}

PROMPT_REQUESTS = {
    "cute": "Без проблем, давай что-нибудь нарисуем. 😎 Напиши текстом, какую картинку ты хочешь получить, а я отправлю запрос нейросети! 🎨",
    "coder": "⚙️ Модуль генерации изображений инициализирован. Введите текстовые параметры (промпт) для отрисовки:",
    "pirate": "Разрази меня гром! 🏴‍☠️ Какую картину поднять на флаг нашего корабля, Капитан? Рожай свой самый дерзкий замысел, а я займусь красками! 🌊",
    "mentor": "Давай попробуем визуализировать твои мысли и внутреннее состояние. ✨ Что бы тебе хотелось сейчас изобразить? Опиши это словами...",
    "snob": "*вздыхает*\nЛадно, человек, отвлеки меня от великих межгалактических вычислений своими каракулями. 🙄 Чего твоя примитивная фантазия желает нарисовать? Опиши, попробую сделать это сносно."
}

def get_reply_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🔄 Перезапустить бота"), KeyboardButton("🎨 Создать картинку")]], resize_keyboard=True)

def get_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎭 Сменить характер", callback_data="btn_char")],
        [InlineKeyboardButton("🧹 Сбросить чат", callback_data="btn_reset"), InlineKeyboardButton("ℹ️ О боте", callback_data="btn_info")]
    ])

def get_char_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌸 Дружелюбный ассистент", callback_data="char_cute")],
        [InlineKeyboardButton("😎 Крутой кодер", callback_data="char_coder")],
        [InlineKeyboardButton("🏴‍☠️ Старый пират", callback_data="char_pirate")],
        [InlineKeyboardButton("🧘 Психолог-ментор", callback_data="char_mentor")],
        [InlineKeyboardButton("🤖 Уставший Сноб", callback_data="char_snob")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="btn_back")]
    ])

def init_chat(uid, c_type="cute"):
    user_characters[uid] = c_type
    user_states[uid] = None
    user_chats[uid] = ai_client.chats.create(model="gemini-3.6-flash", config={"system_instruction": CHARACTERS[c_type]})

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_chat(update.effective_user.id, "cute")
    await update.message.reply_text(
        "Привет! Я твой личный супер-бот **TwinBot**! 🚀\n💬 Пиши вопросы\n📸 Шли фото для анализа\n🎭 Меняй мой характер кнопкой ниже 👇", 
        parse_mode="Markdown", 
        reply_markup=get_reply_keyboard()
    )
    await update.message.reply_text("Управление функциями бота:", reply_markup=get_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    
    if query.data == "btn_char":
        await query.message.edit_text("🎭 **Выбери характер для TwinBot:**", parse_mode="Markdown", reply_markup=get_char_menu())
    elif query.data == "btn_back":
        await query.message.edit_text("Вы вернулись в главное меню 👇", reply_markup=get_menu())
    elif query.data.startswith("char_"):
        c_type = query.data.split("_")
        init_chat(uid, c_type)
        names = {"cute": "Дружелюбного ассистента", "coder": "Крутого кодера", "pirate": "Старого пирата", "mentor": "Психолога-ментора", "snob": "Уставшего Сноба"}
        await query.message.reply_text(f"🎭 Характер изменен на **{names[c_type]}**! Жду сообщений.", parse_mode="Markdown", reply_markup=get_menu())
    elif query.data == "btn_reset":
        init_chat(uid, user_characters.get(uid, "cute"))
        await query.message.reply_text("🧹 Память диалога очищена!", reply_markup=get_menu())
    elif query.data == "btn_info":
        await update.message.reply_text("ℹ️ Я TwinBot на базе **Gemini 3.6 Flash**. Бесплатен и безопасен.", reply_markup=get_menu())

async def draw_logic(update: Update, prompt: str):
    await update.message.reply_chat_action(action="upload_photo")
    try:
        # Ультра-надежная замена пробелов для безопасной ссылки на любом устройстве
        safe_prompt = prompt.replace(" ", "+")
        image_url = f"https://pollinations.ai{safe_prompt}?width=1024&height=1024&nologo=true"
        await update.message.reply_photo(photo=image_url, caption=f"🎨 Готово! Запрос: *{prompt}*", parse_mode="Markdown", reply_markup=get_menu())
    except Exception as e:
        await update.message.reply_text(f"Не удалось нарисовать: {e}", reply_markup=get_menu())

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Укажите запрос после команды. Пример: `/image космос`")
        return
    await draw_logic(update, prompt)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    current_char = user_characters.get(uid, "cute")
    
    if text == "🔄 Перезапустить бота":
        await start_cmd(update, context)
        return
    elif text == "🎨 Создать картинку":
        user_states[uid] = "waiting_for_prompt"
        request_text = PROMPT_REQUESTS.get(current_char, PROMPT_REQUESTS["cute"])
        await update.message.reply_text(request_text)
        return

    if user_states.get(uid) == "waiting_for_prompt":
        user_states[uid] = None
        await draw_logic(update, text)
        return

    if uid not in user_chats: init_chat(uid, "cute")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        res = user_chats[uid].send_message(text)
        await update.message.reply_text(res.text, reply_markup=get_menu())
    except Exception as e:
        await update.message.reply_text(f"Ошибка ИИ: {e}", reply_markup=get_menu())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    p_file = await update.message.photo[-1].get_file()
    path = f"{uid}_t.jpg"
    await p_file.download_to_drive(path)
    cap = update.message.caption if update.message.caption else "Проанализируй это изображение."
    try:
        up_file = ai_client.files.upload(file=path)
        res = ai_client.models.generate_content(model="gemini-3.6-flash", contents=[up_file, cap], config=types.GenerateContentConfig(system_instruction=CHARACTERS[user_characters.get(uid, "cute")]))
        await update.message.reply_text(res.text, reply_markup=get_menu())
        ai_client.files.delete(name=up_file.name)
    except Exception as e:
        await update.message.reply_text(f"Ошибка фото: {e}", reply_markup=get_menu())
    finally:
        if os.path.exists(path): os.remove(path)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("image", generate_image))
    app.add_handler(CommandHandler("img", generate_image))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == '__main__':
    main()
