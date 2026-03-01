import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Состояния
CHOOSING, ASK_QUESTIONS = range(2)

# Временные данные пользователей
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт с кнопками"""
    keyboard = [
        [InlineKeyboardButton("🏠 Аренда квартиры", callback_data='rent')],
        [InlineKeyboardButton("💰 Купля-продажа", callback_data='sale')],
        [InlineKeyboardButton("🔧 Услуги", callback_data='service')]
    ]
    await update.message.reply_text(
        "👋 Добро пожаловать!\n\nВыберите тип договора:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Вопросы для каждого типа договора
    if query.data == 'rent':
        user_data[user_id] = {
            'type': 'rent',
            'questions': [
                '📍 Введите город:',
                '📅 Введите дату (например: 15.03.2025):',
                '👤 ФИО Арендатора:',
                '🏠 Адрес квартиры:',
                '💰 Сумма аренды в месяц (цифрами):',
                '✍️ Сумма прописью:',
                '⏱️ Срок аренды:'
            ],
            'answers': {},
            'step': 0
        }
        await query.edit_message_text(user_data[user_id]['questions'][0])
        return ASK_QUESTIONS
        
    elif query.data == 'sale':
        user_data[user_id] = {
            'type': 'sale',
            'questions': [
                '📍 Введите город:',
                '📅 Введите дату:',
                '👤 ФИО Продавца:',
                '👤 ФИО Покупателя:',
                '📦 Товар:',
                '💰 Сумма (цифрами):',
                '✍️ Сумма прописью:'
            ],
            'answers': {},
            'step': 0
        }
        await query.edit_message_text(user_data[user_id]['questions'][0])
        return ASK_QUESTIONS
        
    elif query.data == 'service':
        user_data[user_id] = {
            'type': 'service',
            'questions': [
                '📍 Введите город:',
                '📅 Введите дату:',
                '👤 ФИО Исполнителя:',
                '👤 ФИО Заказчика:',
                '🔧 Услуга:',
                '💰 Стоимость (цифрами):',
                '✍️ Стоимость прописью:'
            ],
            'answers': {},
            'step': 0
        }
        await query.edit_message_text(user_data[user_id]['questions'][0])
        return ASK_QUESTIONS

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов пользователя"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id not in user_data:
        await update.message.reply_text("Начните с /start")
        return ConversationHandler.END
    
    step = user_data[user_id]['step']
    questions = user_data[user_id]['questions']
    
    # Сохраняем ответ
    user_data[user_id]['answers'][f'q{step}'] = text
    
    # Если есть ещё вопросы
    if step + 1 < len(questions):
        user_data[user_id]['step'] = step + 1
        await update.message.reply_text(f"✅ Принято!\n\n{questions[step + 1]}")
        return ASK_QUESTIONS
    else:
        # Вопросы закончились - формируем договор
        await update.message.reply_text("⏳ Составляю договор...")
        
        answers = user_data[user_id]['answers']
        
        # Формируем текст договора в зависимости от типа
        if user_data[user_id]['type'] == 'rent':
            contract = f"""ДОГОВОР АРЕНДЫ КВАРТИРЫ

г. {answers.get('q0', '______')}                                    «{answers.get('q1', '______')}»

Арендатор: {answers.get('q2', '______')}

Арендодатель передает, а Арендатор принимает в аренду квартиру по адресу: {answers.get('q3', '______')}.

Ежемесячная арендная плата составляет {answers.get('q4', '______')} ({answers.get('q5', '______')}) рублей.

Срок аренды: {answers.get('q6', '______')}.

Подписи сторон:

_______________ /Арендодатель/          _______________ /Арендатор/"""
            
        elif user_data[user_id]['type'] == 'sale':
            contract = f"""ДОГОВОР КУПЛИ-ПРОДАЖИ

г. {answers.get('q0', '______')}                                    «{answers.get('q1', '______')}»

Продавец: {answers.get('q2', '______')}
Покупатель: {answers.get('q3', '______')}

Продавец продал, а Покупатель купил: {answers.get('q4', '______')}.

Сумма сделки: {answers.get('q5', '______')} ({answers.get('q6', '______')}) рублей.

Подписи сторон:

_______________ /Продавец/                _______________ /Покупатель/"""
            
        else:  # service
            contract = f"""ДОГОВОР ОКАЗАНИЯ УСЛУГ

г. {answers.get('q0', '______')}                                    «{answers.get('q1', '______')}»

Исполнитель: {answers.get('q2', '______')}
Заказчик: {answers.get('q3', '______')}

Исполнитель обязуется оказать услуги: {answers.get('q4', '______')}.

Стоимость услуг: {answers.get('q5', '______')} ({answers.get('q6', '______')}) рублей.

Подписи сторон:

_______________ /Исполнитель/              _______________ /Заказчик/"""
        
        # Отправляем договор текстом
        await update.message.reply_text(f"📄 Ваш договор готов:\n\n{contract}")
        
        # Кнопка для нового договора
        keyboard = [[InlineKeyboardButton("🔄 Создать новый договор", callback_data='new')]]
        await update.message.reply_text(
            "Хотите составить ещё один договор?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Очищаем данные пользователя
        del user_data[user_id]
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    user_id = update.message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Действие отменено. Начните с /start")
    return ConversationHandler.END

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ASK_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    logger.info("✅ Бот запущен и готов к работе")
    app.run_polling()

if __name__ == "__main__":
    main()
