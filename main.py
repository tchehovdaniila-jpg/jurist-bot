import os
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

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

# Функция создания PDF
def create_pdf(text, filename="contract.pdf"):
    """Создаёт PDF с русским текстом"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            c = canvas.Canvas(tmp.name, pagesize=A4)
            width, height = A4
            y = height - 50
            
            # Используем стандартный шрифт
            c.setFont("Helvetica", 11)
            
            # Разбиваем текст на строки
            lines = text.split('\n')
            
            for line in lines:
                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 11)
                    y = height - 50
                
                if line.strip():
                    # Кодируем русские буквы
                    try:
                        c.drawString(50, y, line.encode('windows-1251', 'ignore').decode('windows-1251'))
                    except:
                        c.drawString(50, y, line)
                    y -= 15
                else:
                    y -= 10
            
            c.save()
            return tmp.name
    except Exception as e:
        logger.error(f"PDF ошибка: {e}")
        return None

# Настоящие шаблоны договоров
CONTRACTS = {
    'rent': {
        'name': 'Аренда квартиры',
        'questions': [
            '📍 Город:', 
            '📅 Дата (например: 15 марта 2025):',
            '👤 ФИО Арендодателя:', 
            '📄 Паспорт Арендодателя (серия, номер):',
            '🏠 Адрес регистрации Арендодателя:',
            '👤 ФИО Арендатора:', 
            '📄 Паспорт Арендатора:',
            '🏠 Адрес регистрации Арендатора:',
            '🏢 Адрес квартиры:',
            '💰 Сумма аренды в месяц (цифрами):',
            '✍️ Сумма прописью:',
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
2.2. Оплата производится ежемесячно не позднее 10 числа.

3. СРОК ДЕЙСТВИЯ
3.1. Договор действует {11}.

4. ПОДПИСИ СТОРОН
____________________ /Арендодатель/          ____________________ /Арендатор/

Дата: {1}"""
    },
    'sale': {
        'name': 'Купля-продажа',
        'questions': [
            '📍 Город:', 
            '📅 Дата:',
            '👤 ФИО Продавца:', 
            '📄 Паспорт Продавца:',
            '👤 ФИО Покупателя:', 
            '📄 Паспорт Покупателя:',
            '📦 Товар:',
            '💰 Сумма (цифрами):',
            '✍️ Сумма прописью:'
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
____________________ /Продавец/          ____________________ /Покупатель/

Дата: {1}"""
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠 Аренда квартиры", callback_data='rent')],
        [InlineKeyboardButton("💰 Купля-продажа", callback_data='sale')]
    ]
    await update.message.reply_text(
        "Выберите тип договора:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    contract_type = query.data
    user_data[user_id] = {'type': contract_type, 'answers': [], 'step': 0}
    await query.edit_message_text(CONTRACTS[contract_type]['questions'][0])
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        # Формируем текст договора
        contract_text = contract['template'].format(*user_data[user_id]['answers'])
        
        # Создаём PDF
        pdf_path = create_pdf(contract_text)
        
        if pdf_path:
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{contract['name']}.pdf",
                    caption="✅ Ваш договор готов! Осталось подписать."
                )
            # Удаляем временный файл
            os.unlink(pdf_path)
        else:
            # Если PDF не создался - отправляем текстом
            await update.message.reply_text(f"📄 Ваш договор (PDF не создался):\n\n{contract_text}")
        
        del user_data[user_id]
        await update.message.reply_text("Хотите создать ещё? Нажмите /start")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Отменено. /start")
    return ConversationHandler.END

def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    logger.info("✅ Бот с PDF запущен")
    application.run_polling()

if __name__ == "__main__":
    main()
