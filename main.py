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

def force_ascii_text(text):
    """Принудительно преобразует русские буквы в латиницу для гарантированного отображения"""
    replacements = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    
    result = []
    for char in text:
        if char in replacements:
            result.append(replacements[char])
        elif ord(char) < 128:  # ASCII
            result.append(char)
        else:
            result.append('?')  # На случай совсем экзотических символов
    return ''.join(result)

def create_pdf(text, filename="contract.pdf"):
    """Создаёт PDF с гарантированным отображением текста"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            c = canvas.Canvas(tmp.name, pagesize=A4)
            width, height = A4
            y = height - 50
            
            # Используем стандартный шрифт
            c.setFont("Helvetica", 11)
            
            lines = text.split('\n')
            for line in lines:
                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 11)
                    y = height - 50
                
                if line.strip():
                    # Преобразуем русские буквы в латиницу
                    safe_line = force_ascii_text(line)
                    c.drawString(50, y, safe_line)
                    y -= 15
                else:
                    y -= 10
            
            c.save()
            return tmp.name
    except Exception as e:
        logger.error(f"PDF ошибка: {e}")
        return None

# Шаблоны договоров (с пометкой на русском, но в PDF будут транслитом)
CONTRACTS = {
    'rent': {
        'name': 'Аренда квартиры',
        'questions': [
            '📍 Город (City):', 
            '📅 Дата (Date):',
            '👤 ФИО Арендодателя (Landlord name):', 
            '📄 Паспорт Арендодателя (Passport):',
            '🏠 Адрес регистрации Арендодателя (Address):',
            '👤 ФИО Арендатора (Tenant name):', 
            '📄 Паспорт Арендатора (Passport):',
            '🏠 Адрес регистрации Арендатора (Address):',
            '🏢 Адрес квартиры (Apartment address):',
            '💰 Сумма аренды (Rent amount):',
            '✍️ Сумма прописью (In words):',
            '⏱️ Срок аренды (Term):'
        ],
        'template': """DOGOVOR ARENDY KVARTIRY (RENTAL AGREEMENT)

g. {0}                                    «{1}»

Grazhdanin RF {2}, pasport: {3}, zaregistrirovanniy po adresu: {4}, imenuemiy v dal'neyshem "Arendodatel", s odnoy storony, i

Grazhdanin RF {5}, pasport: {6}, zaregistrirovanniy po adresu: {7}, imenuemiy v dal'neyshem "Arendator", s drugoy storony, zaklyuchili nastoyashchiy dogovor:

1. PREDMET DOGOVORA
1.1. Arendodatel peredayet Arendatoru kvartiru po adresu: {8}.

2. ARENDNAYA PLATA
2.1. Plata sostavlyayet {9} ({10}) rubley v mesyats.
2.2. Plata vnositsya ezhemesyachno do 10 chisla.

3. SROK DEYSTVIYA
3.1. Dogovor deystvuyet {11}.

4. PODPISI STORON
____________________ /Arendodatel/          ____________________ /Arendator/

Data: {1}"""
    },
    'sale': {
        'name': 'Kuplya-prodazha',
        'questions': [
            '📍 Gorod (City):', 
            '📅 Data (Date):',
            '👤 FIO Prodavtsa (Seller name):', 
            '📄 Pasport Prodavtsa (Passport):',
            '👤 FIO Pokupatelya (Buyer name):', 
            '📄 Pasport Pokupatelya (Passport):',
            '📦 Tovar (Item):',
            '💰 Summa (Amount):',
            '✍️ Summa propisyu (In words):'
        ],
        'template': """DOGOVOR KUPLI-PRODAZHI (SALES AGREEMENT)

g. {0}                                    «{1}»

Prodavets: {2}, pasport: {3}
Pokupatel: {4}, pasport: {5}

1. PREDMET
1.1. Prodavets prodayet: {6}

2. TSENA
2.1. Summa: {7} ({8}) rubley.

3. PODPISI
____________________ /Prodavets/          ____________________ /Pokupatel/

Data: {1}"""
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠 Arenda (Rent)", callback_data='rent')],
        [InlineKeyboardButton("💰 Kuplya (Sale)", callback_data='sale')]
    ]
    await update.message.reply_text(
        "Vyberite tip dogovora:",
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
        await update.message.reply_text("Nachnite s /start")
        return ConversationHandler.END

    user_data[user_id]['answers'].append(update.message.text)
    step = user_data[user_id]['step']
    contract = CONTRACTS[user_data[user_id]['type']]

    if step + 1 < len(contract['questions']):
        user_data[user_id]['step'] += 1
        await update.message.reply_text(contract['questions'][step + 1])
        return ASKING
    else:
        # Formiruyem tekst dogovora
        contract_text = contract['template'].format(*user_data[user_id]['answers'])
        
        await update.message.reply_text("📄 Sozdayu PDF...")
        
        # Sozdayom PDF
        pdf_path = create_pdf(contract_text)
        
        if pdf_path:
            with open(pdf_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{contract['name']}.pdf",
                    caption="✅ Vash dogovor gotov!"
                )
            os.unlink(pdf_path)
        else:
            await update.message.reply_text(f"📄 Vash dogovor (PDF vremenno nedostupen):\n\n{contract_text}")
        
        del user_data[user_id]
        await update.message.reply_text("Hotite sozdat' eshche? Nazhmite /start")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Otmeneno. /start")
    return ConversationHandler.END

def main():
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

    logger.info("✅ Bot zapushchen (100% PDF garantiya)")
    application.run_polling()

if __name__ == "__main__":
    main()
