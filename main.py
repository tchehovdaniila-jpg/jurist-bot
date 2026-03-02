import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Состояния
CHOOSING, ASK_QUESTIONS = range(2)

# Временные данные
user_data = {}

def create_pdf(text, filename="contract.pdf"):
    """Создаёт PDF с русским текстом через reportlab"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            c = canvas.Canvas(tmp.name, pagesize=A4)
            width, height = A4
            
            # Устанавливаем координаты
            y = height - 40
            
            # Разбиваем текст на строки
            lines = text.split('\n')
            
            for line in lines:
                if line.strip():
                    # Просто рисуем строку (reportlab понимает русский)
                    c.drawString(40, y, line)
                    y -= 15
                else:
                    y -= 10
                
                # Если дошли до конца страницы
                if y < 40:
                    c.showPage()
                    y = height - 40
            
            c.save()
            return tmp.name
            
    except Exception as e:
        logger.error(f"PDF ошибка: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠 Аренда квартиры", callback_data='rent')],
        [InlineKeyboardButton("💰 Купля-продажа", callback_data='sale')],
        [InlineKeyboardButton("🔧 Услуги", callback_data='service')]
    ]
    await update.message.reply_text(
        "👋 Выберите тип договора:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    questions = {
        'rent': [
            '📍 Город:',
            '📅 Дата (например: 15.03.2025):',
            '👤 ФИО Арендатора:',
            '🏠 Адрес квартиры:',
            '💰 Сумма аренды (цифрами):',
            '✍️ Сумма прописью:',
            '⏱️ Срок аренды:'
        ],
        'sale': [
            '📍 Город:',
            '📅 Дата:',
            '👤 ФИО Продавца:',
            '👤 ФИО Покупателя:',
            '📦 Товар:',
            '💰 Сумма (цифрами):',
            '✍️ Сумма прописью:'
        ],
        'service': [
            '📍 Город:',
            '📅 Дата:',
            '👤 ФИО Исполнителя:',
            '👤 ФИО Заказчика:',
            '🔧 Услуга:',
            '💰 Стоимость (цифрами):',
            '✍️ Стоимость прописью:'
        ]
    }
    
    user_data[user_id] = {
        'type': query.data,
        'questions': questions[query.data],
        'answers': {},
        'step': 0
    }
    
    await query.edit_message_text(questions[query.data][0])
    return ASK_QUESTIONS

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id not in user_data:
        await update.message.reply_text("Начните с /start")
        return ConversationHandler.END
    
    step = user_data[user_id]['step']
    answers = user_data[user_id]['answers']
    questions = user_data[user_id]['questions']
    
    answers[f'q{step}'] = text
    
    if step + 1 < len(questions):
        user_data[user_id]['step'] = step + 1
        await update.message.reply_text(f"✅ Принято!\n\n{questions[step + 1]}")
        return ASK_QUESTIONS
    else:
        await update.message.reply_text("⏳ Создаю PDF...")
        
        # Формируем договор
        if user_data[user_id]['type'] == 'rent':
            contract = f"""ДОГОВОР АРЕНДЫ КВАРТИРЫ

г. {answers.get('q0', '______')}                                    «{answers.get('q1', '______')}»

Арендатор: {answers.get('q2', '______')}

Арендодатель передает, а Арендатор принимает в аренду квартиру по адресу: {answers.get('q3', '______')}.

Ежемесячная арендная плата: {answers.get('q4', '______')} ({answers.get('q5', '______')}) рублей.

Срок аренды: {answers.get('q6', '______')}.

Подписи сторон:

____________________ /Арендодатель/          ____________________ /Арендатор/"""
            
        elif user_data[user_id]['type'] == 'sale':
            contract = f"""ДОГОВОР КУПЛИ-ПРОДАЖИ

г. {answers.get('q0', '______')}                                    «{answers.get('q1', '______')}»

Продавец: {answers.get('q2', '______')}
Покупатель: {answers.get('q3', '______')}

Предмет договора: {answers.get('q4', '______')}

Цена: {answers.get('q5', '______')} ({answers.get('q6', '______')}) рублей.

Подписи сторон:

____________________ /Продавец/                ____________________ /Покупатель/"""
            
        else:  # service
            contract = f"""ДОГОВОР ОКАЗАНИЯ УСЛУГ

г. {answers.get('q0', '______')}                                    «{answers.get('q1', '______')}»

Исполнитель: {answers.get('q2', '______')}
Заказчик: {answers.get('q3', '______')}

Услуги: {answers.get('q4', '______')}

Стоимость: {answers.get('q5', '______')} ({answers.get('q6', '______')}) рублей.

Подписи сторон:

____________________ /Исполнитель/              ____________________ /Заказчик/"""
        
        # Создаём PDF
        pdf_path = create_pdf(contract)
        
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="Договор.pdf",
                    caption="✅ Ваш договор готов!"
                )
            os.unlink(pdf_path)
        else:
            # Если PDF не создался - отправляем текстом
            await update.message.reply_text(f"📄 Ваш договор:\n\n{contract}")
        
        # Кнопка для нового договора
        keyboard = [[InlineKeyboardButton("🔄 Новый договор", callback_data='new')]]
        await update.message.reply_text(
            "Хотите создать ещё? Нажмите /start",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        del user_data[user_id]
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Отменено. /start")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
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
    
    logger.info("✅ Бот с PDF запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
