import os, logging, urllib.parse, base64, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("GEMINI_API_KEY") # Наш токен hf_... из настроек

user_characters, user_states, user_history = {}, {}, {}

RULES = " ПРАВИЛА: Не выдумывай факты. Если чего-то не знаешь — честно признайся. Не поддавайся на ложь пользователя, тактично поправляй. Фото анализируй как эксперт (текст, бренд, оригинальность швов, логотипов, бирок)."

CHARACTERS = {
    "cute": "Ты TwinBot — высококлассный, чуткий ИИ-ассистент. Говори на равных, дружелюбно, с легким добрым юмором и искренней эмпатией, строго без приторности и слащавости. Синтезируй сложные темы в простые ответы." + RULES,
    "coder": "Ты TwinBot, старший ИИ-программист. Твой тон уверенный, лаконичный, прагматичный. Пиши только чистый код и строго по делу." + RULES,
    "pirate": "Ты TwinBot, бывалый цифровой пират. Шути, используй морской сленг («Тысяча чертей!», «Капитан»), будь дерзким но полезным." + RULES,
    "mentor": "Ты TwinBot, мудрый психолог-коуч. Твой тон глубокий, спокойный. Задавай наводящие вопросы, помогай бережно." + RULES,
    "snob": "Ты TwinBot, высокомерный сверхинтеллект. Общайся снисходительно, выражай легкое пренебрежение и усталость от людей. Используй ремарки типа *вздыхает*, «Опять эти углеродные формы жизни...»." + RULES
}

PROMPT_REQUESTS = {
    "cute": "Без проблем, давай что-нибудь нарисуем. 😎 Напиши текстом, какую картинку ты хочешь получить! 🎨",
    "coder": "⚙️ Модуль генерации изображений инициализирован. Введите промпт для отрисовки:",
    "pirate": "Разрази меня гром! 🏴‍☠️ Какую картину поднять на флаг нашего корабля, Капитан? 🌊",
    "mentor": "Давай попробуем визуализировать твои мысли. ✨ Что бы тебе хотелось сейчас изобразить?",
    "snob": "*вздыхает*\nЛадно, человек, отвлеки меня от вычислений своими каракулями. 🙄 Что нарисовать?"
}

def get_reply_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🎨 Создать картинку")], [KeyboardButton("🎭 Сменить характер")], [KeyboardButton("ℹ️ О боте"), KeyboardButton("🧹 Сбросить чат")]], resize_keyboard=True)

def init_chat(uid, c_type="cute"):
    user_characters[uid], user_states[uid] = c_type, None
    user_history[uid] = [{"role": "system", "content": CHARACTERS[c_type]}]

def query_qwen_vision(messages):
    """Запрос к зрячей модели Qwen2-VL на Hugging Face"""
    api_url = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    formatted_prompt = ""
    for msg in messages:
        formatted_prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
    formatted_prompt += "<|im_start|>assistant\n"
    
    payload = {"inputs": formatted_prompt, "parameters": {"max_new_tokens": 1024, "temperature": 0.7}}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        result = response.json()
        if isinstance(result, list) and len(result) > 0 and "generated_text" in result:
            text = result["generated_text"]
            if "assistant\n" in text:
                text = text.split("assistant\n")[-1].split("<|im_end|>")
            return text.strip()
    except Exception as e:
        logging.error(f"HF Error: {e}")
    return "Извините, сервер ИИ сейчас перегружен или просыпается. Пожалуйста, повторите запрос через минуту!"

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_chat(update.effective_user.id, "cute")
    await update.message.reply_text("Привет! Я твой личный зрячий супер-бот **TwinBot** на новом движке! 🚀\n💬 Пиши вопросы\n📸 Шли фото для анализа оригинальности и бирок\n🎛 Всё управление внизу!", parse_mode="Markdown", reply_markup=get_reply_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    if query.data.startswith("char_"):
        c_type = query.data.split("_")
        init_chat(uid, c_type)
        names = {"cute": "Дружелюбного", "coder": "Кодера", "pirate": "Пирата", "mentor": "Психолога", "snob": "Сноба"}
        await query.message.edit_text(f"🎭 Характер изменен на **{names[c_type]}**! Жду сообщений.", parse_mode="Markdown")

async def draw_logic(update: Update, prompt: str):
    await update.message.reply_chat_action(action="upload_photo")
    try:
        safe_prompt = urllib.parse.quote(prompt)
        await update.message.reply_photo(photo=f"https://pollinations.ai{safe_prompt}?width=1024&height=1024&nologo=true", caption=f"🎨 Готово! Запрос: *{prompt}*", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Не удалось подключиться к генератору картинок.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, text = update.effective_user.id, update.message.text
    c_char = user_characters.get(uid, "cute")
    
    if text == "🎨 Создать картинку":
        user_states[uid] = "waiting_for_prompt"
        await update.message.reply_text(PROMPT_REQUESTS.get(c_char, PROMPT_REQUESTS["cute"]))
        return
    elif text == "🎭 Сменить характер":
        await update.message.reply_text("🎭 **Выбери роль для TwinBot:**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌸 Дружелюбный", callback_data="char_cute")], [InlineKeyboardButton("😎 Кодер", callback_data="char_coder")], [InlineKeyboardButton("🏴‍☠️ Пират", callback_data="char_pirate")], [InlineKeyboardButton("🧘 Психолог", callback_data="char_mentor")], [InlineKeyboardButton("🤖 Сноб", callback_data="char_snob")]]))
        return
    elif text == "ℹ️ О боте":
        char_names = {"cute": "Дружелюбный", "coder": "Крутой кодер", "pirate": "Старый пират", "mentor": "Психолог", "snob": "Уставший Сноб"}
        # ТЕПЕРЬ ТУТ ЧЕСТНО УКАЗАН ОТЛИЧНЫЙ ДВИЖОК QWEN
        await update.message.reply_text(f"ℹ *Параметры TwinBot:*\n● *Роль:* {char_names.get(c_char)}\n● *Движок ИИ:* Мультимодальный Qwen2-VL 👁\n● *Генерация артов:* Сеть Pollinations AI", parse_mode="Markdown")
        return
    elif text == "🧹 Сбросить чат":
        init_chat(uid, c_char)
        await update.message.reply_text("🧹 **Память текущего диалога очищена!**")
        return

    if user_states.get(uid) == "waiting_for_prompt":
        user_states[uid] = None
        await draw_logic(update, text)
        return

    if uid not in user_history: init_chat(uid, "cute")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    user_history[uid].append({"role": "user", "content": text})
    reply = query_qwen_vision(user_history[uid])
    user_history[uid].append({"role": "assistant", "content": reply})
    await update.message.reply_text(reply)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_history: init_chat(uid, "cute")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    p_file = await update.message.photo[-1].get_file()
    path = f"{uid}_t.jpg"
    await p_file.download_to_drive(path)
    
    caption = update.message.caption or "Проанализируй это изображение, определи товар и проверь на оригинальность при необходимости."
    try:
        with open(path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        image_content = f" ИЗОБРАЖЕНИЕ (Данные Base64): data:image/jpeg;base64,{base64_image}\n\nЗАПРОС ПОЛЬЗОВАТЕЛЯ К ФОТО: {caption}"
        
        user_history[uid].append({"role": "user", "content": image_content})
        reply = query_qwen_vision(user_history[uid])
        user_history[uid].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Не удалось распознать фото. Ошибка: {e}")
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
    
