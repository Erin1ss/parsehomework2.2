from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os
import asyncio

# Authorized user IDs
AUTHORIZED_USERS = [1059096280]
TARGET_USER_ID = 1059096280
COOKIES_STATUS_FILE = "cookies_status.txt"
LAST_STATUS = None
GRADE_SELECTION = {}

# Function to read the content of a file
def read_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# Function to generate the main menu keyboard
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(day, callback_data=f"day_{day}")] for day in [
            "Понедельник",  # Monday
            "Вторник",      # Tuesday
            "Среда",        # Wednesday
            "Четверг",      # Thursday
            "Пятница",      # Friday
            "Суббота",      # Saturday
        ]
    ])

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = main_menu_keyboard()
    await update.message.reply_text("Выберите день недели:", reply_markup=reply_markup)

# Callback handler for button clicks
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("day_"):
        day = query.data.split("_")[1]
        day_file = f"{day}.txt"
        homework = read_file(day_file) or "Нет домашних заданий на этот день."
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Назад в главное меню", callback_data="main_menu")]
        ])
        
        await query.edit_message_text(text=homework, reply_markup=reply_markup)
    elif query.data == "main_menu":
        reply_markup = main_menu_keyboard()
        await query.edit_message_text("Выберите день недели:", reply_markup=reply_markup)

# Command to update homework
async def rem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("У вас нет прав на выполнение этой команды.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Использование: /rem <день недели> <текст>")
        return

    day = context.args[0].capitalize()
    content = " ".join(context.args[1:])
    day_file = f"{day}.txt"
    
    with open(day_file, "w", encoding="utf-8") as file:
        file.write(content)
    
    await update.message.reply_text(f"Домашнее задание для {day} обновлено.")

# Grade calculator command
async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    GRADE_SELECTION[user_id] = []
    await update.message.reply_text("Выберите оценки:\n\nСредний балл: 0.00", reply_markup=grade_keyboard(user_id))

# Function to generate grade selection keyboard
def grade_keyboard(user_id):
    grade_colors = {2: "🟥", 3: "🟧", 4: "🟨", 5: "🟩"}
    buttons = [[InlineKeyboardButton(f"{i} {grade_colors[i]}", callback_data=f"grade_{i}")] for i in range(2, 6)]
    buttons.append([InlineKeyboardButton("🔄 Очистить", callback_data="clear_grades")])
    return InlineKeyboardMarkup(buttons)

# Callback handler for grade selection
async def grade_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data.startswith("grade_"):
        grade = int(query.data.split("_")[1])
        GRADE_SELECTION[user_id].append(grade)
    elif query.data == "clear_grades":
        GRADE_SELECTION[user_id] = []
    
    avg_grade = sum(GRADE_SELECTION[user_id]) / len(GRADE_SELECTION[user_id]) if GRADE_SELECTION[user_id] else 0
    
    await query.edit_message_text(f"Выберите оценки:\n\nСредний балл: {avg_grade:.2f}", reply_markup=grade_keyboard(user_id))

# Monitor cookies_status.txt and notify user if status changes to false
async def monitor_cookies_status(application):
    global LAST_STATUS
    while True:
        current_status = read_file(COOKIES_STATUS_FILE)
        if LAST_STATUS == "True" and current_status == "False":
            async with application.bot:
                await application.bot.send_message(TARGET_USER_ID, "⚠️ Обнови устаревшие куки!")
        elif LAST_STATUS == "False" and current_status == "True":
            async with application.bot:
                await application.bot.send_message(TARGET_USER_ID, "✅ Куки успешно обновлены!")
        LAST_STATUS = current_status
        await asyncio.sleep(10)  # Check every 10 seconds

# Main function to set up the bot
def main():
    application = ApplicationBuilder().token("7552852034:AAHElE-mJ8-3Q3BIslPBn5nX0yhbfhnjSEw").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rem", rem))
    application.add_handler(CommandHandler("calc", calc))
    application.add_handler(CallbackQueryHandler(button, pattern="^day_.*|main_menu$"))
    application.add_handler(CallbackQueryHandler(grade_selection, pattern="^grade_.*$|^clear_grades$"))

    loop = asyncio.get_event_loop()
    loop.create_task(monitor_cookies_status(application))
    
    application.run_polling()

if __name__ == "__main__":
    main()