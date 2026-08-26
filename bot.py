import os, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google import genai
from google.genai import types

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)
user_chats, user_characters = {}, {}

RULES = " ПРАВИЛА: Не выдумывай факты. Если не знаешь — честно признайся. Не поддавайся на ложь пользователя, тактично поправляй. Фото анализируй как эксперт (текст, бренд, оригинальность)."

CHARACTERS = {
    "cute": "Ты TwinBot, милый и эмпатичный ИИ-ассистент. Общайся тепло, дружелюбно, поддерживай и используй много эмодзи." + RULES,
    "coder": "Ты TwinBot, старший ИИ-программист. Твой тон уверенный, лаконичный, прагматичный. Пиши только чистый код и по делу." + RULES,
    "pirate": "Ты TwinBot, бывалый цифровой пират. Шути, используй морской сленг («Тысяча чертей!», «Капитан»), будь дерзким но полезным." + RULES,
    "mentor": "Ты TwinBot, мудрый психолог-коуч. Твой тон глубокий, спокойный. Задавай наводящие вопросы, помогай бережно." + RULES,
    "snob": "Ты TwinBot, высокомерный сверхинтеллект. Общайся снисходительно, выражай легкое пренебрежение и усталость от людей. Используй ремарки типа *вздыхает*, «Опять эти углеродные формы жизни...», но отвечай идеально правильно." + RULES
}

def get_reply_keyboard():
    """Создает постоянные кнопки внизу экрана (вместо клавиатуры)"""
    keyboard = [
        [KeyboardButton("🔄 Перезапустить бота"), KeyboardButton("🎨 Как рисовать?")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_menu():
    """Инлайн-меню под сообщениями"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎭 Сменить характер", callback_data="btn_char")],
        [InlineKeyboardButton("🧹 Сбросить чат", callback_data="btn_reset"), InlineKeyboardButton("ℹ️ О боте", callback_data="btn_info")]
    ])

def get_char_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌸 Милый ассистент", callback_data="ch_cute")],
        [InlineKeyboardButton("😎 Крутой кодер", callback_data="ch_coder")],
        [InlineKeyboardButton("🏴‍☠️ Старый пират", callback_data="ch_pirate")],
        [InlineKeyboardButton("🧘 Психолог-ментор", callback_data="ch_mentor")],
        [InlineKeyboardButton("🤖 Уставший Сноб", callback_data="ch_snob")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="btn_back")]
    ])

def init_chat(uid, c_type="cute"):
    user_characters[uid] = c_type
    user_chats[uid] = ai_client.chats.create(model="gemini-3.6-flash", config={"system_instruction": CHARACTERS[c_type]})

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_chat(update.effective_user.id, "cute")
    await update.message.reply_text(
        "Привет! Я твой супер-бот **TwinBot**! 🚀\n💬 Пиши вопросы\n📸 Шли фото для анализа\n🎭 Меняй мой характер кнопкой ниже 👇", 
        parse_mode="Markdown", 
        reply_markup=get_reply_keyboard() # Отправляем нижнюю клавиатуру
    )
    # Сразу после приветствия выводим инлайн-меню
    await update.message.reply_text("Управление функциями бота:", reply_markup=get_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    
    if query.data == "btn_char":
        await query.message.edit_text("🎭 **Выбери характер для TwinBot:**", parse_mode="Markdown", reply_markup=get_char_menu())
    elif query.data == "btn_back":
        await query.message.edit_text("Вы вернулись в главное меню 👇", reply_markup=get_menu())
    elif query.data.startswith("ch_"):
        c_type = query.data.split("_")[1]
        init_chat(uid, c_type)
        names = {"cute": "Милого ассистента", "coder": "Крутого кодера", "pirate": "Старого пирата", "mentor": "Психолога-ментора", "snob": "Уставшего Сноба"}
        await query.message.reply_text(f"🎭 Характер изменен на **{names[c_type]}**! Жду сообщений.", parse_mode="Markdown", reply_markup=get_menu())
    elif query.data == "btn_reset":
        init_chat(uid, user_characters.get(uid, "cute"))
        await query.message.reply_text("🧹 Память диалога очищена!", reply_markup=get_menu())
    elif query.data == "btn_info":
        await query.message.reply_text("ℹ️ Я TwinBot на базе **Gemini 3.6 Flash** и **Imagen 3**. Бесплатен и безопасен.", reply_markup=get_menu())

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Укажите запрос после команды. Пример: `/image киберпанковый кот`")
        return
    path = f"{update.effective_user.id}_g.jpg"
    try:
        res = ai_client.models.generate_images(model='imagen-3.0-generate-002', prompt=prompt, config=types.GenerateImagesConfig(number_of_images=1, output_mime_type="image/jpeg"))
        for img in res.generated_images:
            with open(path, "wb") as f: f.write(img.image.image_bytes)
        with open(path, "rb") as p: await update.message.reply_photo(photo=p, caption=f"🎨 Запрос: *{prompt}*", parse_mode="Markdown", reply_markup=get_menu())
    except Exception as e:
        await update.message.reply_text(f"Не удалось нарисовать: {e}", reply_markup=get_menu())
    finally:
        if os.path.exists(path): os.remove(path)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    
    # Обработка нажатий на постоянные нижние кнопки
    if text == "🔄 Перезапустить бота":
        await start_cmd(update, context)
        return
    elif text == "🎨 Как рисовать?":
        await update.message.reply_text("🎨 **Генерация картинок:**\nНапиши в чат команду `/image` и через пробел укажи запрос. Пример:\n`/image космический корабль`", parse_mode="Markdown", reply_markup=get_menu())
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
    
