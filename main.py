import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

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
    """Создаёт PDF с русским текстом (Helvetica + win1251)"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            c = canvas.Canvas(tmp.name, pagesize=A4)
            width, height = A4
            
            # Используем Helvetica (есть везде)
            c.setFont("Helvetica", 12)
            
            y = height - 40
            lines = text.split('\n')
            
            for line in lines:
                if line.strip():
                    # Кодируем русские буквы в win1251
                    try:
                        line_enc = line.encode('windows-1251', 'ignore').decode('windows-1251')
                    except:
                        line_enc = line.encode('ascii', 'ignore').decode('ascii')
                    
                    c.drawString(40, y, line_enc)
                    y -= 15
                else:
                    y -= 10
                
                if y < 40:
                    c.showPage()
                    c.setFont("Helvetica", 12)
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
    
    # Вопросы и шаблоны
    if query.data == 'rent':
        user_data[user_id] = {
            'type': 'rent',
            'questions': [
                '📍 Введите город:',
                '📅 Введите дату (например: 15 марта 2025 года):',
                '👤 ФИО Арендодателя (полностью):',
                '📄 Паспортные данные Арендодателя (серия, номер, кем выдан):',
                '🏠 Адрес регистрации Арендодателя:',
                '👤 ФИО Арендатора (полностью):',
                '📄 Паспортные данные Арендатора:',
                '🏠 Адрес регистрации Арендатора:',
                '🏢 Адрес сдаваемой квартиры:',
                '💰 Сумма аренды в месяц (цифрами):',
                '✍️ Сумма аренды прописью:',
                '⏱️ Срок аренды (например: 11 месяцев):'
            ],
            'answers': {},
            'step': 0
        }
    elif query.data == 'sale':
        user_data[user_id] = {
            'type': 'sale',
            'questions': [
                '📍 Город:',
                '📅 Дата:',
                '👤 ФИО Продавца:',
                '📄 Паспорт Продавца:',
                '👤 ФИО Покупателя:',
                '📄 Паспорт Покупателя:',
                '📦 Товар (что продаётся):',
                '💰 Сумма сделки (цифрами):',
                '✍️ Сумма прописью:'
            ],
            'answers': {},
            'step': 0
        }
    else:  # service
        user_data[user_id] = {
            'type': 'service',
            'questions': [
                '📍 Город:',
                '📅 Дата:',
                '👤 ФИО Исполнителя:',
                '👤 ФИО Заказчика:',
                '🔧 Услуга (что делается):',
                '💰 Стоимость (цифрами):',
                '✍️ Стоимость прописью:',
                '⏱️ Срок оказания:'
            ],
            'answers': {},
            'step': 0
        }
    
    await query.edit_message_text(user_data[user_id]['questions'][0])
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
        await update.message.reply_text("⏳ Создаю договор...")
        
        # Полноценный договор аренды
        if user_data[user_id]['type'] == 'rent':
            contract = f"""ДОГОВОР АРЕНДЫ КВАРТИРЫ

г. {answers.get('q0', '______')}                                 «{answers.get('q1', '______')}»

    Гражданин РФ {answers.get('q2', '______')}, паспорт: {answers.get('q3', '______')}, зарегистрированный по адресу: {answers.get('q4', '______')}, именуемый в дальнейшем "Арендодатель", с одной стороны, и

    Гражданин РФ {answers.get('q5', '______')}, паспорт: {answers.get('q6', '______')}, зарегистрированный по адресу: {answers.get('q7', '______')}, именуемый в дальнейшем "Арендатор", с другой стороны, заключили настоящий договор о нижеследующем:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Арендодатель передает, а Арендатор принимает во временное владение и пользование квартиру, расположенную по адресу: {answers.get('q8', '______')}.
1.2. Квартира передается в состоянии, пригодном для проживания.

2. АРЕНДНАЯ ПЛАТА
2.1. Арендная плата за пользование квартирой составляет {answers.get('q9', '______')} ({answers.get('q10', '______')}) рублей в месяц.
2.2. Арендная плата вносится ежемесячно не позднее 10 числа каждого месяца.

3. СРОК ДЕЙСТВИЯ ДОГОВОРА
3.1. Договор действует в течение {answers.get('q11', '______')}.
3.2. Если ни одна из сторон не заявит о расторжении за 30 дней, договор считается продленным.

4. ПОДПИСИ СТОРОН

Арендодатель: ____________________              Арендатор: ____________________

Дата: ____________________"""
            
        elif user_data[user_id]['type'] == 'sale':
            contract = f"""ДОГОВОР КУПЛИ-ПРОДАЖИ

г. {answers.get('q0', '______')}                                 «{answers.get('q1', '______')}»

    Гражданин РФ {answers.get('q2', '______')}, паспорт: {answers.get('q3', '______')}, именуемый в дальнейшем "Продавец", и

    Гражданин РФ {answers.get('q4', '______')}, паспорт: {answers.get('q5', '______')}, именуемый в дальнейшем "Покупатель", заключили настоящий договор:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Продавец продает, а Покупатель покупает: {answers.get('q6', '______')}.

2. ЦЕНА ДОГОВОРА
2.1. Цена составляет {answers.get('q7', '______')} ({answers.get('q8', '______')}) рублей.
2.2. Расчет производится в момент подписания договора.

3. ПЕРЕДАЧА
3.1. Право собственности переходит к Покупателю после полной оплаты.

4. ПОДПИСИ

Продавец: ____________________              Покупатель: ____________________

Дата: ____________________"""
            
        else:  # услуги
            contract = f"""ДОГОВОР ОКАЗАНИЯ УСЛУГ

г. {answers.get('q0', '______')}                                 «{answers.get('q1', '______')}»

    Гражданин РФ {answers.get('q2', '______')}, именуемый в дальнейшем "Исполнитель", и

    Гражданин РФ {answers.get('q3', '______')}, именуемый в дальнейшем "Заказчик", заключили договор:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Исполнитель обязуется оказать услуги: {answers.get('q4', '______')}.

2. СТОИМОСТЬ УСЛУГ
2.1. Стоимость составляет {answers.get('q5', '______')} ({answers.get('q6', '______')}) рублей.

3. СРОКИ
3.1. Услуги оказываются в срок: {answers.get('q7', '______')}.

4. ПОДПИСИ

Исполнитель: ____________________              Заказчик: ____________________

Дата: ____________________"""
        
        # Создаём PDF
        pdf_path = create_pdf(contract)
        
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="Договор.pdf",
                    caption="✅ Ваш договор готов. Осталось подписать."
                )
            os.unlink(pdf_path)
        else:
            await update.message.reply_text(f"📄 Ваш договор (PDF временно недоступен):\n\n{contract}")
        
        # Кнопка нового договора
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
    
    logger.info("✅ Бот с договорами запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
