import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("Нет токена!")
    exit(1)

# Состояния
CHOOSING, ASKING = range(2)
user_data = {}

# Простые шаблоны
CONTRACTS = {
    'rent': {
        'name': 'Аренда',
        'questions': ['Город:', 'Дата:', 'Имя:', 'Адрес:', 'Сумма:'],
        'template': 'ДОГОВОР АРЕНДЫ\n\nГород: {}\nДата: {}\nИмя: {}\nАдрес: {}\nСумма: {} руб.\n\nПодписи:\n___________'
    },
    'sale': {
        'name': 'Покупка',
        'questions': ['Город:', 'Дата:', 'Имя:', 'Товар:', 'Сумма:'],
        'template': 'ДОГОВОР КУПЛИ-ПРОДАЖИ\n\nГород: {}\nДата: {}\nИмя: {}\nТовар: {}\nСумма: {} руб.\n\nПодписи:\n___________'
    }
}

def start(update, context):
    keyboard = [[InlineKeyboardButton("🏠 Аренда", callback_data='rent')],
                [InlineKeyboardButton("💰 Покупка", callback_data='sale')]]
    update.message.reply_text("Выберите:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {'type': query.data, 'answers': [], 'step': 0}
    query.edit_message_text(CONTRACTS[query.data]['questions'][0])
    return ASKING

def handle_answer(update, context):
    user_id = update.message.from_user.id
    if user_id not in user_data:
        update.message.reply_text("Начните с /start")
        return ConversationHandler.END

    user_data[user_id]['answers'].append(update.message.text)
    step = user_data[user_id]['step']
    contract = CONTRACTS[user_data[user_id]['type']]

    if step + 1 < len(contract['questions']):
        user_data[user_id]['step'] += 1
        update.message.reply_text(contract['questions'][step + 1])
        return ASKING
    else:
        result = contract['template'].format(*user_data[user_id]['answers'])
        update.message.reply_text(f"✅ Договор:\n\n{result}")
        del user_data[user_id]
        update.message.reply_text("Новый? /start")
        return ConversationHandler.END

def cancel(update, context):
    user_id = update.message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    update.message.reply_text("Отменено. /start")
    return ConversationHandler.END

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={ASKING: [MessageHandler(Filters.text & ~Filters.command, handle_answer)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)

    logger.info("✅ Бот запускается...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
