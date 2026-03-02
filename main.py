import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (из переменных окружения)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Состояния диалога
CHOOSING, ASKING = range(2)

# Хранилище данных пользователей
user_data = {}

# Шаблоны договоров
CONTRACTS = {
    'rent': {
        'name': 'Аренда квартиры',
        'questions': ['Город:', 'Дата:', 'Ваше имя:'],
        'template': 'Договор аренды\n\nГород: {}\nДата: {}\nИмя: {}'
    },
    'sale': {
        'name': 'Купля-продажа',
        'questions': ['Город:', 'Дата:', 'Ваше имя:'],
        'template': 'Договор купли-продажи\n\nГород: {}\nДата: {}\nИмя: {}'
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
    
    user_data[user_id] = {
        'type': contract_type,
        'answers': [],
        'step': 0
    }
    
    await query.edit_message_text(
        CONTRACTS[contract_type]['questions'][0]
    )
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов пользователя"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id not in user_data:
        await update.message.reply_text("Начните с /start")
        return ConversationHandler.END
    
    user_data[user_id]['answers'].append(text)
    current_step = user_data[user_id]['step']
    contract = CONTRACTS[user_data[user_id]['type']]
    
    if current_step + 1 < len(contract['questions']):
        user_data[user_id]['step'] += 1
        await update.message.reply_text(contract['questions'][current_step + 1])
        return ASKING
    else:
        # Все вопросы заданы
        result = contract['template'].format(*user_data[user_id]['answers'])
        await update.message.reply_text(f"✅ Готово:\n\n{result}")
        
        del user_data[user_id]
        
        # Кнопка для нового договора
        keyboard = [[InlineKeyboardButton("🔄 Новый договор", callback_data='new')]]
        await update.message.reply_text(
            "Хотите ещё?",
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
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    logger.info("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
