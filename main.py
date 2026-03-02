import os
import logging
import tempfile
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Состояния
SELECTING, FILLING = range(2)

# Хранилище данных пользователей
user_sessions = {}

# === ШАБЛОНЫ ДОГОВОРОВ ===
CONTRACT_TEMPLATES = {
    'rent': {
        'name': 'Аренда квартиры',
        'questions': [
            '📍 Город:',
            '📅 Дата (например: 15 марта 2025):',
            '👤 ФИО Арендодателя полностью:',
            '📄 Паспорт Арендодателя (серия, номер, кем выдан):',
            '🏠 Адрес регистрации Арендодателя:',
            '👤 ФИО Арендатора полностью:',
            '📄 Паспорт Арендатора:',
            '🏠 Адрес регистрации Арендатора:',
            '🏢 Адрес сдаваемой квартиры:',
            '💰 Сумма аренды в месяц (цифрами):',
            '✍️ Сумма аренды прописью:',
            '⏱️ Срок аренды:'
        ],
        'template': """ДОГОВОР АРЕНДЫ КВАРТИРЫ

г. {0}                                    «{1}»

Гражданин РФ {2}, паспорт: {3}, зарегистрированный по адресу: {4}, именуемый в дальнейшем "Арендодатель", с одной стороны, и

Гражданин РФ {5}, паспорт: {6}, зарегистрированный по адресу: {7}, именуемый в дальнейшем "Арендатор", с другой стороны, заключили настоящий договор:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Арендодатель передает Арендатору квартиру по адресу: {8}.

2. АРЕНДНАЯ ПЛАТА
2.1. Плата составляет {9} ({10}) рублей в месяц.

3. СРОК ДЕЙСТВИЯ
3.1. Договор действует {11}.

4. ПОДПИСИ СТОРОН

_______________ /Арендодатель/          _______________ /Арендатор/

Дата: {1}"""
    },
    'sale': {
        'name': 'Купля-продажа',
        'questions': [
            '📍 Город:', '📅 Дата:', '👤 ФИО Продавца:', '📄 Паспорт Продавца:',
            '👤 ФИО Покупателя:', '📄 Паспорт Покупателя:', '📦 Товар:',
            '💰 Сумма (цифрами):', '✍️ Сумма прописью:'
        ],
        'template': """ДОГОВОР КУПЛИ-ПРОДАЖИ

г. {0}                                    «{1}»

Продавец: {2}, паспорт: {3}
Покупатель: {4}, паспорт: {5}

1. ПРЕДМЕТ
1.1. Продавец продает: {6}

2. ЦЕНА
2.1. Сумма: {7} ({8}) рублей.

3. ПОДПИСИ

_______________ /Продавец/          _______________ /Покупатель/

Дата: {1}"""
    },
    'service': {
        'name': 'Услуги',
        'questions': [
            '📍 Город:', '📅 Дата:', '👤 ФИО Исполнителя:', '👤 ФИО Заказчика:',
            '🔧 Услуга:', '💰 Стоимость (цифрами):', '✍️ Стоимость прописью:', '⏱️ Срок:'
        ],
        'template': """ДОГОВОР ОКАЗАНИЯ УСЛУГ

г. {0}                                    «{1}»

Исполнитель: {2}
Заказчик: {3}

1. УСЛУГИ
1.1. Исполнитель оказывает: {4}

2. СТОИМОСТЬ
2.1. Цена: {5} ({6}) рублей.

3. СРОК
3.1. Услуги оказываются: {7}

4. ПОДПИСИ

_______________ /Исполнитель/          _______________ /Заказчик/

Дата: {1}"""
    }
}

def generate_pdf(text, filename='contract.pdf'):
    """Генерация PDF с русским текстом"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            c = canvas.Canvas(tmp.name, pagesize=A4)
            width, height = A4
            y = height - 50
            
            # Используем стандартный шрифт с кодировкой win1251
            c.setFont('Helvetica', 11)
            
            for line in text.split('\n'):
                if y < 50:
                    c.showPage()
                    c.setFont('Helvetica', 11)
                    y = height - 50
                
                if line.strip():
                    # Кодируем для поддержки русского
                    try:
                        c.drawString(50, y, line.encode('win1251').decode('win1251'))
                    except:
                        c.drawString(50, y, line)
                    y -= 15
                else:
                    y -= 10
            
            c.save()
            return tmp.name
    except Exception as e:
        logger.error(f"PDF Error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🏠 Аренда квартиры", callback_data='rent')],
        [InlineKeyboardButton("💰 Купля-продажа", callback_data='sale')],
        [InlineKeyboardButton("🔧 Услуги", callback_data='service')]
    ]
    await update.message.reply_text(
        "👋 Добро пожаловать!\nВыберите тип договора:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    contract_type = query.data
    
    # Создаем сессию пользователя
    user_sessions[user_id] = {
        'type': contract_type,
        'answers': [],
        'step': 0,
        'total': len(CONTRACT_TEMPLATES[contract_type]['questions'])
    }
    
    # Отправляем первый вопрос
    await query.edit_message_text(
        f"📝 {CONTRACT_TEMPLATES[contract_type]['name']}\n\n"
        f"Вопрос 1/{user_sessions[user_id]['total']}:\n"
        f"{CONTRACT_TEMPLATES[contract_type]['questions'][0]}"
    )
    return FILLING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id not in user_sessions:
        await update.message.reply_text("Начните с /start")
        return ConversationHandler.END
    
    session = user_sessions[user_id]
    contract = CONTRACT_TEMPLATES[session['type']]
    
    # Сохраняем ответ
    session['answers'].append(text)
    session['step'] += 1
    
    # Если есть еще вопросы
    if session['step'] < session['total']:
        await update.message.reply_text(
            f"✅ Принято!\n\n"
            f"Вопрос {session['step'] + 1}/{session['total']}:\n"
            f"{contract['questions'][session['step']]}"
        )
        return FILLING
    
    # Все вопросы заданы — формируем договор
    await update.message.reply_text("⚡ Создаю договор...")
    
    # Формируем текст договора
    contract_text = contract['template'].format(*session['answers'])
    
    # Создаем PDF
    pdf_path = generate_pdf(contract_text)
    
    if pdf_path:
        with open(pdf_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"{contract['name']}.pdf",
                caption="✅ Готово! Подпишите и распечатайте."
            )
        os.unlink(pdf_path)
    else:
        # Если PDF не создался — отправляем текст
        await update.message.reply_text(f"📄 Договор:\n\n{contract_text}")
    
    # Предлагаем создать новый
    keyboard = [[InlineKeyboardButton("🔄 Новый договор", callback_data='new')]]
    await update.message.reply_text(
        "Хотите еще? Нажмите /start",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Очищаем сессию
    del user_sessions[user_id]
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    user_id = update.message.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text("Отменено. /start")
    return ConversationHandler.END

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback)],
        states={
            FILLING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    logger.info("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
