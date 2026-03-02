import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (обязательно должен быть в переменных окружения Render)
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("Ошибка: BOT_TOKEN не найден в переменных окружения!")
    # Выходим, чтобы Render показал ошибку в логах
    exit(1)

# Состояния диалога
CHOOSING, ASKING = range(2)
user_data = {}

# Шаблоны договоров
CONTRACTS = {
    'rent': {
        'name': 'Аренда квартиры',
        'questions': ['📍 Город:', '📅 Дата:', '👤 Ваше имя:', '🏠 Адрес:', '💰 Сумма:'],
        'template': 'ДОГОВОР АРЕНДЫ\n\nГород: {}\nДата: {}\nИмя: {}\nАдрес: {}\nСумма: {} руб.\n\nПодписи:\n___________'
    },
    'sale': {
        'name': 'Купля-продажа',
        'questions': ['📍 Город:', '📅 Дата:', '👤 Ваше имя:', '📦 Товар:', '💰 Сумма:'],
        'template': 'ДОГОВОР КУПЛИ-ПРОДАЖИ\n\nГород: {}\nДата: {}\nИмя: {}\nТовар: {}\nСумма: {} руб.\n\nПодписи:\n___________'
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    keyboard = [
        [InlineKeyboardButton("🏠 Аренда", callback_data='rent')],
        [InlineKeyboardButton("💰 Покупка", callback_data='sale')]
    ]
    await update.message.reply_text(
        "Выберите тип договора:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    contract_type = query.data
    user_data[user_id] = {'type': contract_type, 'answers': [], 'step': 0}
    await query.edit_message_text(CONTRACTS[contract_type]['questions'][0])
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов"""
    user_id = update.message.from_user.id
    if user_id not in user_data:
        await update.message.reply_text("Начните с /start")
        return ConversationHandler.END

    user_data[user_id]['answers'].append(update.message.text)
    step = user_data[user_id]['step']
    contract = CONTRACTS[user_data[user_id]['type']]

    if step + 1 < len(contract['questions']):
        user_data[user_id]['step'] += 1
        await update.message.reply_text(contract['questions'][step + 1])
        return ASKING
    else:
        result = contract['template'].format(*user_data[user_id]['answers'])
        await update.message.reply_text(f"✅ Готово:\n\n{result}")
        del user_data[user_id]

        # Кнопка для нового договора
        keyboard = [[InlineKeyboardButton("🔄 Новый договор", callback_data='new')]]
        await update.message.reply_text(
            "Хотите создать ещё? Нажмите /start",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена действия"""
    user_id = update.message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Отменено. /start")
    return ConversationHandler.END

def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # Создаем обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    logger.info("✅ Бот запущен и начинает опрос Telegram...")
    # Запускаем бота (это бесконечный цикл)
    app.run_polling()

if __name__ == "__main__":
    main()
