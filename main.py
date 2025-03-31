import logging
import pandas as pd
import json
from copy import deepcopy
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)
import pytz

timezone = pytz.timezone('Europe/Moscow')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка токена
try:
    with open("token.txt", "r") as f:
        TOKEN = f.read().strip()
except FileNotFoundError:
    logger.error("Файл token.txt не найден!")
    exit(1)

# Инициализация DataFrame
try:
    df = pd.read_csv("expenses.csv")
except FileNotFoundError:
    df = pd.DataFrame(columns=["user_id", "date", "label", "amount"])

# Файл для хранения имен пользователей
USER_NAMES_FILE = "user_names.json"

# Загрузка имен пользователей из файла
def load_user_names():
    try:
        if Path(USER_NAMES_FILE).exists():
            with open(USER_NAMES_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка при загрузке имен пользователей: {e}")
    return {}

# Сохранение имен пользователей в файл
def save_user_names():
    try:
        with open(USER_NAMES_FILE, "w") as f:
            json.dump(user_names, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении имен пользователей: {e}")

# Словарь для хранения имен пользователей {user_id: name}
user_names = load_user_names()

# Состояния диалога
GET_NAME, SELECT_LABEL, INPUT_CUSTOM_LABEL, INPUT_AMOUNT = range(4)

def get_user_labels(user_name):
    """Получает список уникальных меток трат для конкретного пользователя"""
    user_expenses = df[df["user_id"] == user_name]
    if not user_expenses.empty:
        labels = user_expenses["label"].unique().tolist()
        if "Другое" not in labels:
            labels.append("Другое")
        return labels
    return ["Другое"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога, проверка имени пользователя."""
    user_id = str(update.message.from_user.id)
    
    # Если имя уже есть, пропускаем этап представления
    if user_id in user_names:
        user_name = user_names[user_id]
        labels = get_user_labels(user_name)
        reply_keyboard = [labels[i:i+2] for i in range(0, len(labels), 2)]
        
        await update.message.reply_text(
            f"Привет, {user_name}! Выберите категорию траты:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return SELECT_LABEL
    else:
        await update.message.reply_text(
            "Привет! Как тебя зовут?",
            reply_markup=ReplyKeyboardRemove()
        )
        return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода имени пользователя."""
    user_id = str(update.message.from_user.id)
    name = update.message.text.strip()
    
    # Проверяем, есть ли уже такое имя у другого пользователя
    if name in user_names.values():
        await update.message.reply_text(
            "Это имя уже занято. Пожалуйста, выберите другое имя:",
            reply_markup=ReplyKeyboardRemove()
        )
        return GET_NAME
    
    # Сохраняем имя пользователя
    user_names[user_id] = name
    save_user_names()
    
    labels = get_user_labels(name)
    reply_keyboard = [labels[i:i+2] for i in range(0, len(labels), 2)]
    
    await update.message.reply_text(
        f"Приятно познакомиться, {name}! Выберите категорию траты:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return SELECT_LABEL

async def select_label(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора категории траты."""
    label = update.message.text
    context.user_data["label"] = label
    
    if label == "Другое":
        await update.message.reply_text(
            "Введите название траты:",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_CUSTOM_LABEL
    
    await update.message.reply_text(
        "Введите сумму траты:\nДля отмены нажмите /cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    return INPUT_AMOUNT

async def input_custom_label(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ручного ввода названия траты."""
    custom_label = update.message.text
    context.user_data["label"] = custom_label
    
    await update.message.reply_text(
        "Введите сумму траты:\nДля отмены нажмите /cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    return INPUT_AMOUNT

async def input_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода суммы траты и сохранение."""
    try:
        amount = float(update.message.text)
        user_data = context.user_data
        
        # Добавляем трату в DataFrame
        global df
        new_row = {
            "user_id": user_names[str(update.message.from_user.id)],
            "date": pd.Timestamp.now(timezone).strftime("%Y-%m-%d"),
            "label": user_data["label"],
            "amount": amount
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv("expenses.csv", index=False)
        
        await update.message.reply_text(
            f"Трата сохранена, {user_names.get(str(update.message.from_user.id), 'друг')}!\n"
            f"Категория: {user_data['label']}\n"
            f"Сумма: {amount} руб.\n"
            "Нажмите /start для новой записи."
            "\nНажмите /delete_last для удаления последней траты"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число (например: 1500.50):")
        return INPUT_AMOUNT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущей операции."""
    user_name = user_names.get(str(update.message.from_user.id), "друг")
    await update.message.reply_text(
        f"Действие отменено, {user_name}.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def delete_last(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет последнюю запись пользователя."""
    global df
    
    user_id = str(update.message.from_user.id)
    
    if user_id not in user_names:
        await update.message.reply_text("Вы еще не сохраняли траты!")
        return
    
    user_name = user_names[user_id]
    user_entries = df[df["user_id"] == user_name]
    
    if user_entries.empty:
        await update.message.reply_text("У вас нет сохраненных трат!")
        return
    
    # Находим последнюю запись
    last_entry_index = user_entries.index[-1]
    
    # Удаляем запись
    df = df.drop(last_entry_index)
    df.to_csv("expenses.csv", index=False)
    
    await update.message.reply_text("Последняя трата удалена!")

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            SELECT_LABEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_label)
            ],
            INPUT_CUSTOM_LABEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_custom_label)
            ],
            INPUT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_amount)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("delete_last", delete_last))
    
    application.run_polling()

if __name__ == "__main__":
    main()
