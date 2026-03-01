import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from fpdf import FPDF
import tempfile
from datetime import datetime

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Состояния для разговора
CHOOSING, FILLING_ARENDA, FILLING_POKUPKA, FILLING_USLUGI = range(4)

# Временные данные пользователей
user_data = {}

# Класс для PDF с поддержкой русского
class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # Добавляем поддержку Unicode
        self.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        
    def header(self):
        # Можно добавить логотип или шапку
        pass
        
    def footer(self):
        # Номера страниц
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.cell(0, 10, f'Страница {self.page_no()}', 0, 0, 'C')

# Шаблоны договоров
TEMPLATES = {
    "аренда": {
        "name": "Договор аренды квартиры",
        "fields": [
            {"name": "город", "question": "Введите город:"},
            {"name": "дата", "question": "Введите дату (например: 15 марта 2025):"},
            {"name": "arendodatel_fio", "question": "ФИО Арендодателя:"},
            {"name": "arendodatel_pasport", "question": "Паспорт Арендодателя (серия и номер):"},
            {"name": "arendodatel_vydan", "question": "Кем выдан паспорт Арендодателя:"},
            {"name": "arendodatel_adres", "question": "Адрес регистрации Арендодателя:"},
            {"name": "arendator_fio", "question": "ФИО Арендатора:"},
            {"name": "arendator_pasport", "question": "Паспорт Арендатора (серия и номер):"},
            {"name": "arendator_vydan", "question": "Кем выдан паспорт Арендатора:"},
            {"name": "arendator_adres", "question": "Адрес регистрации Арендатора:"},
            {"name": "adres_kvartiry", "question": "Адрес квартиры:"},
            {"name": "summa", "question": "Сумма аренды в месяц (цифрами):"},
            {"name": "summa_propis", "question": "Сумма аренды прописью:"},
            {"name": "srok", "question": "Срок аренды (например: 11 месяцев):"}
        ],
        "template": """ДОГОВОР АРЕНДЫ КВАРТИРЫ

г. {город}                                    «{дата}»

Гражданин(ка) РФ {arendodatel_fio}, паспорт: {arendodatel_pasport}, выдан: {arendodatel_vydan}, зарегистрированный по адресу: {arendodatel_adres}, именуемый в дальнейшем "Арендодатель", с одной стороны, и

Гражданин(ка) РФ {arendator_fio}, паспорт: {arendator_pasport}, выдан: {arendator_vydan}, зарегистрированный по адресу: {arendator_adres}, именуемый в дальнейшем "Арендатор", с другой стороны, совместно именуемые "Стороны", заключили настоящий договор о нижеследующем:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Арендодатель передает, а Арендатор принимает во временное владение и пользование квартиру, расположенную по адресу: {adres_kvartiry}.
1.2. Квартира передается в состоянии, пригодном для проживания.

2. АРЕНДНАЯ ПЛАТА И РАСЧЕТЫ
2.1. Арендная плата за пользование квартирой составляет {summa} ({summa_propis}) рублей в месяц.
2.2. Арендная плата вносится Арендатором ежемесячно не позднее 10 числа каждого месяца.

3. СРОК ДЕЙСТВИЯ ДОГОВОРА
3.1. Настоящий договор вступает в силу с момента подписания и действует в течение {srok}.
3.2. Если ни одна из Сторон не заявит о расторжении договора за 30 дней до окончания срока, договор считается продленным на тот же срок.

4. ОБЯЗАННОСТИ СТОРОН
4.1. Арендодатель обязан передать квартиру в чистом и пригодном для проживания состоянии.
4.2. Арендатор обязан своевременно вносить арендную плату и поддерживать квартиру в надлежащем состоянии.

5. ПОДПИСИ СТОРОН
__________________                          __________________
(Арендодатель)                              (Арендатор)

Дата: __________________"""
    },
    
    "покупка": {
        "name": "Договор купли-продажи",
        "fields": [
            {"name": "город", "question": "Введите город:"},
            {"name": "дата", "question": "Введите дату (например: 15 марта 2025):"},
            {"name": "prodavec_fio", "question": "ФИО Продавца:"},
            {"name": "prodavec_pasport", "question": "Паспорт Продавца (серия и номер):"},
            {"name": "prodavec_adres", "question": "Адрес регистрации Продавца:"},
            {"name": "pokupatel_fio", "question": "ФИО Покупателя:"},
            {"name": "pokupatel_pasport", "question": "Паспорт Покупателя (серия и номер):"},
            {"name": "pokupatel_adres", "question": "Адрес регистрации Покупателя:"},
            {"name": "tovar", "question": "Что продается (наименование товара):"},
            {"name": "summa", "question": "Сумма сделки (цифрами):"},
            {"name": "summa_propis", "question": "Сумма сделки прописью:"}
        ],
        "template": """ДОГОВОР КУПЛИ-ПРОДАЖИ

г. {город}                                    «{дата}»

Гражданин(ка) РФ {prodavec_fio}, паспорт: {prodavec_pasport}, зарегистрированный по адресу: {prodavec_adres}, именуемый в дальнейшем "Продавец", с одной стороны, и

Гражданин(ка) РФ {pokupatel_fio}, паспорт: {pokupatel_pasport}, зарегистрированный по адресу: {pokupatel_adres}, именуемый в дальнейшем "Покупатель", с другой стороны, заключили настоящий договор о нижеследующем:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Продавец обязуется передать в собственность Покупателя, а Покупатель обязуется принять и оплатить следующее имущество: {tovar}.

2. ЦЕНА И ПОРЯДОК РАСЧЕТОВ
2.1. Цена имущества составляет {summa} ({summa_propis}) рублей.
2.2. Покупатель обязуется оплатить полную стоимость имущества в момент подписания настоящего договора.

3. ПЕРЕДАЧА ИМУЩЕСТВА
3.1. Продавец обязуется передать имущество Покупателю в момент подписания договора.
3.2. Право собственности на имущество переходит к Покупателю после полной оплаты.

4. ПОДПИСИ СТОРОН
__________________                          __________________
(Продавец)                                    (Покупатель)

Дата: __________________"""
    },
    
    "услуги": {
        "name": "Договор оказания услуг",
        "fields": [
            {"name": "город", "question": "Введите город:"},
            {"name": "дата", "question": "Введите дату (например: 15 марта 2025):"},
            {"name": "ispolnitel_fio", "question": "ФИО Исполнителя:"},
            {"name": "ispolnitel_pasport", "question": "Паспорт Исполнителя (серия и номер):"},
            {"name": "zakazchik_fio", "question": "ФИО Заказчика:"},
            {"name": "zakazchik_pasport", "question": "Паспорт Заказчика (серия и номер):"},
            {"name": "usluga", "question": "Какие услуги оказываются:"},
            {"name": "summa", "question": "Стоимость услуг (цифрами):"},
            {"name": "summa_propis", "question": "Стоимость услуг прописью:"},
            {"name": "srok", "question": "Срок оказания услуг:"}
        ],
        "template": """ДОГОВОР ОКАЗАНИЯ УСЛУГ

г. {город}                                    «{дата}»

Гражданин(ка) РФ {ispolnitel_fio}, паспорт: {ispolnitel_pasport}, именуемый в дальнейшем "Исполнитель", с одной стороны, и

Гражданин(ка) РФ {zakazchik_fio}, паспорт: {zakazchik_pasport}, именуемый в дальнейшем "Заказчик", с другой стороны, заключили настоящий договор о нижеследующем:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Исполнитель обязуется оказать Заказчику следующие услуги: {usluga}.
1.2. Заказчик обязуется принять и оплатить оказанные услуги.

2. СТОИМОСТЬ УСЛУГ И ПОРЯДОК ОПЛАТЫ
2.1. Стоимость услуг составляет {summa} ({summa_propis}) рублей.
2.2. Оплата производится в следующем порядке: 100% предоплата / 50% предоплата, 50% после оказания услуг.

3. СРОКИ ОКАЗАНИЯ УСЛУГ
3.1. Услуги оказываются в срок: {srok}.

4. ПРАВА И ОБЯЗАННОСТИ СТОРОН
4.1. Исполнитель обязан оказать услуги качественно и в срок.
4.2. Заказчик обязан оплатить услуги в соответствии с условиями договора.

5. ПОДПИСИ СТОРОН
__________________                          __________________
(Исполнитель)                                 (Заказчик)

Дата: __________________"""
    }
}

def create_pdf_from_template(template_text, filename="contract.pdf"):
    """Создаёт PDF из текста шаблона с поддержкой русского"""
    try:
        # Создаём PDF
        pdf = PDF()
        pdf.add_page()
        pdf.set_font('DejaVu', '', 12)
        
        # Разбиваем текст на строки
        lines = template_text.split('\n')
        
        # Добавляем строки
        for line in lines:
            if line.strip() == '':
                pdf.ln(5)
            else:
                # Для русских букв используем Unicode
                pdf.multi_cell(0, 8, line)
        
        # Сохраняем
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf.output(tmp.name)
            return tmp.name
            
    except Exception as e:
        logger.error(f"Ошибка PDF: {e}")
        # Пробуем без специальных шрифтов
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Helvetica', size=12)
            
            lines = template_text.split('\n')
            for line in lines:
                if line.strip() == '':
                    pdf.ln(5)
                else:
                    # Пробуем windows-1251
                    line_win = line.encode('windows-1251', 'ignore').decode('windows-1251')
                    pdf.cell(0, 10, txt=line_win, ln=True)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                pdf.output(tmp.name)
                return tmp.name
        except:
            return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и меню"""
    keyboard = [
        [InlineKeyboardButton("🏠 Аренда квартиры", callback_data='arend')],
        [InlineKeyboardButton("💰 Купля-продажа", callback_data='pokupka')],
        [InlineKeyboardButton("🔧 Услуги", callback_data='uslugi')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Добро пожаловать!\n\n"
        "Я помогу составить договор. Просто выберите нужный тип:",
        reply_markup=reply_markup
    )
    return CHOOSING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {}
    
    if query.data == 'arend':
        user_data[user_id]['contract_type'] = 'аренда'
        user_data[user_id]['fields'] = TEMPLATES['аренда']['fields'].copy()
        user_data[user_id]['current_field'] = 0
        user_data[user_id]['answers'] = {}
        
        await query.edit_message_text(
            f"📝 {TEMPLATES['аренда']['name']}\n\n"
            f"Вопрос 1 из {len(TEMPLATES['аренда']['fields'])}:\n"
            f"{TEMPLATES['аренда']['fields'][0]['question']}"
        )
        return FILLING_ARENDA
        
    elif query.data == 'pokupka':
        user_data[user_id]['contract_type'] = 'покупка'
        user_data[user_id]['fields'] = TEMPLATES['покупка']['fields'].copy()
        user_data[user_id]['current_field'] = 0
        user_data[user_id]['answers'] = {}
        
        await query.edit_message_text(
            f"📝 {TEMPLATES['покупка']['name']}\n\n"
            f"Вопрос 1 из {len(TEMPLATES['покупка']['fields'])}:\n"
            f"{TEMPLATES['покупка']['fields'][0]['question']}"
        )
        return FILLING_POKUPKA
        
    elif query.data == 'uslugi':
        user_data[user_id]['contract_type'] = 'услуги'
        user_data[user_id]['fields'] = TEMPLATES['услуги']['fields'].copy()
        user_data[user_id]['current_field'] = 0
        user_data[user_id]['answers'] = {}
        
        await query.edit_message_text(
            f"📝 {TEMPLATES['услуги']['name']}\n\n"
            f"Вопрос 1 из {len(TEMPLATES['услуги']['fields'])}:\n"
            f"{TEMPLATES['услуги']['fields'][0]['question']}"
        )
        return FILLING_USLUGI
        
    elif query.data == 'help':
        keyboard = [
            [InlineKeyboardButton("🏠 Аренда", callback_data='arend')],
            [InlineKeyboardButton("💰 Купля", callback_data='pokupka')],
            [InlineKeyboardButton("🔧 Услуги", callback_data='uslugi')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❓ Как это работает:\n\n"
            "1. Выберите тип договора\n"
            "2. Ответьте на вопросы\n"
            "3. Получите готовый PDF\n"
            "4. Распечатайте и подпишите\n\n"
            "Выберите тип:",
            reply_markup=reply_markup
        )
        return CHOOSING

async def handle_arend_filling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заполнение анкеты для аренды"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id not in user_data:
        await update.message.reply_text("Начните с /start")
        return ConversationHandler.END
    
    current = user_data[user_id]['current_field']
    fields = user_data[user_id]['fields']
    field_name = fields[current]['name']
    
    user_data[user_id]['answers'][field_name] = text
    
    if current + 1 < len(fields):
        user_data[user_id]['current_field'] = current + 1
        next_field = fields[current + 1]
        await update.message.reply_text(f"✅ Принято!\n\n{next_field['question']}")
        return FILLING_ARENDA
    else:
        await update.message.reply_text("⏳ Создаю договор...")
        
        template_data = TEMPLATES[user_data[user_id]['contract_type']]
        template_text = template_data['template']
        
        filled_text = template_text
        for key, value in user_data[user_id]['answers'].items():
            filled_text = filled_text.replace(f"{{{key}}}", value)
        
        pdf_path = create_pdf_from_template(filled_text)
        
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=f"{template_data['name']}.pdf",
                    caption="✅ Ваш договор готов!\n\nОсталось распечатать и подписать."
                )
            os.unlink(pdf_path)
            
            keyboard = [
                [InlineKeyboardButton("🏠 Аренда", callback_data='arend')],
                [InlineKeyboardButton("💰 Купля", callback_data='pokupka')],
                [InlineKeyboardButton("🔧 Услуги", callback_data='uslugi')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Хотите создать ещё один договор?",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка создания PDF. Попробуйте позже.")
        
        del user_data[user_id]
        return ConversationHandler.END

async def handle_pokupka_filling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заполнение для покупки"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id not in user_data:
        await update.message.reply_text("Начните с /start")
        return ConversationHandler.END
    
    current = user_data[user_id]['current_field']
    fields = user_data[user_id]['fields']
    field_name = fields[current]['name']
    
    user_data[user_id]['answers'][field_name] = text
    
    if current + 1 < len(fields):
        user_data[user_id]['current_field'] = current + 1
        next_field = fields[current + 1]
        await update.message.reply_text(f"✅ Принято!\n\n{next_field['question']}")
        return FILLING_POKUPKA
    else:
        await update.message.reply_text("⏳ Создаю договор...")
        
        template_data = TEMPLATES[user_data[user_id]['contract_type']]
        template_text = template_data['template']
        
        filled_text = template_text
        for key, value in user_data[user_id]['answers'].items():
            filled_text = filled_text.replace(f"{{{key}}}", value)
        
        pdf_path = create_pdf_from_template(filled_text)
        
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=f"{template_data['name']}.pdf",
                    caption="✅ Ваш договор готов!\n\nОсталось распечатать и подписать."
                )
            os.unlink(pdf_path)
            
            keyboard = [
                [InlineKeyboardButton("🏠 Аренда", callback_data='arend')],
                [InlineKeyboardButton("💰 Купля", callback_data='pokupka')],
                [InlineKeyboardButton("🔧 Услуги", callback_data='uslugi')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Хотите создать ещё один договор?",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка создания PDF. Попробуйте позже.")
        
        del user_data[user_id]
        return ConversationHandler.END

async def handle_uslugi_filling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заполнение для услуг"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id not in user_data:
        await update.message.reply_text("Начните с /start")
        return ConversationHandler.END
    
    current = user_data[user_id]['current_field']
    fields = user_data[user_id]['fields']
    field_name = fields[current]['name']
    
    user_data[user_id]['answers'][field_name] = text
    
    if current + 1 < len(fields):
        user_data[user_id]['current_field'] = current + 1
        next_field = fields[current + 1]
        await update.message.reply_text(f"✅ Принято!\n\n{next_field['question']}")
        return FILLING_USLUGI
    else:
        await update.message.reply_text("⏳ Создаю договор...")
        
        template_data = TEMPLATES[user_data[user_id]['contract_type']]
        template_text = template_data['template']
        
        filled_text = template_text
        for key, value in user_data[user_id]['answers'].items():
            filled_text = filled_text.replace(f"{{{key}}}", value)
        
        pdf_path = create_pdf_from_template(filled_text)
        
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=f"{template_data['name']}.pdf",
                    caption="✅ Ваш договор готов!\n\nОсталось распечатать и подписать."
                )
            os.unlink(pdf_path)
            
            keyboard = [
                [InlineKeyboardButton("🏠 Аренда", callback_data='arend')],
                [InlineKeyboardButton("💰 Купля", callback_data='pokupka')],
                [InlineKeyboardButton("🔧 Услуги", callback_data='uslugi')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Хотите создать ещё один договор?",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка создания PDF. Попробуйте позже.")
        
        del user_data[user_id]
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    user_id = update.message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Действие отменено. Начните заново с /start")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    keyboard = [
        [InlineKeyboardButton("🏠 Аренда", callback_data='arend')],
        [InlineKeyboardButton("💰 Купля", callback_data='pokupka')],
        [InlineKeyboardButton("🔧 Услуги", callback_data='uslugi')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "❓ Помощь:\n\n"
        "1. Выберите тип договора\n"
        "2. Ответьте на вопросы\n"
        "3. Получите PDF\n\n"
        "Выберите тип:",
        reply_markup=reply_markup
    )

def main():
    """Запуск"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            FILLING_ARENDA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_arend_filling)],
            FILLING_POKUPKA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pokupka_filling)],
            FILLING_USLUGI: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_uslugi_filling)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    
    logger.info("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
