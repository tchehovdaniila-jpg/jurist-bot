import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fpdf import FPDF
import tempfile
import re

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токены
BOT_TOKEN = os.environ.get('BOT_TOKEN')
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')

# API SiliconFlow
API_URL = "https://api.siliconflow.com/v1/chat/completions"

# Шаблоны договоров
TEMPLATES = {
    "аренда": """ДОГОВОР АРЕНДЫ КВАРТИРЫ

г. ______________                «___» __________ 20__ г.

Гражданин(ка) РФ ______________________________, паспорт: серия ____ № _________, выдан ______________________________, зарегистрированный по адресу: ______________________________, именуемый в дальнейшем "Арендодатель", с одной стороны, и

Гражданин(ка) РФ ______________________________, паспорт: серия ____ № _________, выдан ______________________________, зарегистрированный по адресу: ______________________________, именуемый в дальнейшем "Арендатор", с другой стороны, совместно именуемые "Стороны", заключили настоящий договор о нижеследующем:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Арендодатель передает, а Арендатор принимает во временное владение и пользование квартиру, расположенную по адресу: ______________________________.
1.2. Квартира передается в состоянии, пригодном для проживания.

2. ПЛАТЕЖИ И РАСЧЕТЫ
2.1. Арендная плата за пользование квартирой составляет _______ (__________) рублей в месяц.
2.2. Оплата производится ежемесячно не позднее _____ числа каждого месяца.

3. СРОК ДЕЙСТВИЯ ДОГОВОРА
3.1. Настоящий договор вступает в силу с момента подписания и действует до «___» __________ 20__ г.

4. ПОДПИСИ СТОРОН
Арендодатель: _______________ /___________________/
Арендатор: _______________ /___________________/""",

    "купля": """ДОГОВОР КУПЛИ-ПРОДАЖИ

г. ______________                «___» __________ 20__ г.

Гражданин(ка) РФ ______________________________, именуемый в дальнейшем "Продавец", и

Гражданин(ка) РФ ______________________________, именуемый в дальнейшем "Покупатель", заключили настоящий договор о нижеследующем:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Продавец обязуется передать в собственность Покупателя, а Покупатель обязуется принять и оплатить следующий товар: ______________________________.

2. ЦЕНА И ПОРЯДОК РАСЧЕТОВ
2.1. Цена товара составляет _______ (__________) рублей.
2.2. Покупатель обязуется оплатить товар в срок до «___» __________ 20__ г.

3. ПРАВА И ОБЯЗАННОСТИ СТОРОН
3.1. Продавец обязан передать товар надлежащего качества.
3.2. Покупатель обязан принять и оплатить товар.

4. ПОДПИСИ СТОРОН
Продавец: _______________ /___________________/
Покупатель: _______________ /___________________/""",

    "услуги": """ДОГОВОР ОКАЗАНИЯ УСЛУГ

г. ______________                «___» __________ 20__ г.

Индивидуальный предприниматель ______________________________, именуемый в дальнейшем "Исполнитель", с одной стороны, и

Гражданин(ка) РФ ______________________________, именуемый в дальнейшем "Заказчик", с другой стороны, заключили настоящий договор о нижеследующем:

1. ПРЕДМЕТ ДОГОВОРА
1.1. Исполнитель обязуется оказать Заказчику следующие услуги: ______________________________.
1.2. Заказчик обязуется принять и оплатить оказанные услуги.

2. СТОИМОСТЬ И ПОРЯДОК ОПЛАТЫ
2.1. Стоимость услуг составляет _______ (__________) рублей.
2.2. Оплата производится в следующем порядке: ______________________________.

3. СРОКИ ОКАЗАНИЯ УСЛУГ
3.1. Услуги оказываются в срок с «___» __________ 20__ г. по «___» __________ 20__ г.

4. ПОДПИСИ СТОРОН
Исполнитель: _______________ /___________________/
Заказчик: _______________ /___________________/"""
}

def clean_text_for_pdf(text):
    """Очищает текст от спецсимволов для PDF"""
    # Заменяем спецсимволы на безопасные
    text = text.replace('—', '-')
    text = text.replace('«', '"')
    text = text.replace('»', '"')
    text = text.replace('…', '...')
    # Удаляем управляющие символы
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return text

def create_pdf_from_text(text, filename="contract.pdf"):
    """Создаёт PDF файл из текста"""
    try:
        # Очищаем текст
        clean_text = clean_text_for_pdf(text)
        
        # Создаём PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Устанавливаем шрифт (UTF-8)
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)  # Попробуем стандартный
        pdf.set_font('Helvetica', size=12)  # Запасной вариант
        
        # Разбиваем текст на строки
        lines = clean_text.split('\n')
        
        # Добавляем каждую строку
        for line in lines:
            # Если строка пустая, добавляем перевод строки
            if line.strip() == '':
                pdf.ln(5)
            else:
                # Кодируем в latin-1, заменяя проблемные символы
                try:
                    pdf.cell(0, 10, txt=line, ln=True)
                except:
                    # Если ошибка, пробуем упрощённую версию
                    simple_line = line.encode('latin-1', 'ignore').decode('latin-1')
                    pdf.cell(0, 10, txt=simple_line, ln=True)
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdf.output(tmp.name)
            return tmp.name
    except Exception as e:
        logger.error(f"Ошибка создания PDF: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для создания договоров.\n"
        "Напиши: аренда, купля, услуги\n"
        "Я пришлю готовый PDF-файл с договором!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    # Проверяем шаблоны
    if "аренда" in text:
        template = TEMPLATES.get("аренда", "")
        await update.message.reply_text("⏳ Создаю PDF...")
        
        # Создаём PDF
        pdf_path = create_pdf_from_text(template, "dogovor_arendy.pdf")
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename="Договор_аренды.pdf",
                    caption="✅ Ваш договор аренды готов!"
                )
            # Удаляем временный файл
            os.unlink(pdf_path)
        else:
            await update.message.reply_text("❌ Ошибка создания PDF. Вот текст договора:\n\n" + template)
    
    elif "покупка" in text:
    template = TEMPLATES.get("покупка", "")
    await update.message.reply_text("⏳ Создаю PDF...")
    
    pdf_path = create_pdf_from_text(template, "dogovor_kupli.pdf")
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename="Договор_купли_продажи.pdf",
                caption="✅ Ваш договор купли-продажи готов!"
            )
        os.unlink(pdf_path)
    else:
        await update.message.reply_text("❌ Ошибка создания PDF. Вот текст договора:\n\n" + template)
    
    elif "услуги" in text:
        template = TEMPLATES.get("услуги", "")
        await update.message.reply_text("⏳ Создаю PDF...")
        
        pdf_path = create_pdf_from_text(template, "dogovor_uslugi.pdf")
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename="Договор_оказания_услуг.pdf",
                    caption="✅ Ваш договор на услуги готов!"
                )
            os.unlink(pdf_path)
        else:
            await update.message.reply_text("❌ Ошибка создания PDF. Вот текст договора:\n\n" + template)
    
    else:
        # Если нет шаблона - нейросеть
        await update.message.reply_text("⏳ Обращаюсь к нейросети...")
        
        try:
            headers = {
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-ai/DeepSeek-R1",
                "messages": [{"role": "user", "content": text}]
            }
            async with httpx.AsyncClient() as client:
                r = await client.post(API_URL, json=payload, headers=headers, timeout=30)
                r.raise_for_status()
                answer = r.json()['choices'][0]['message']['content']
                
                # Создаём PDF из ответа нейросети
                await update.message.reply_text("📄 Создаю PDF...")
                pdf_path = create_pdf_from_text(answer, "generated.pdf")
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as pdf_file:
                        await update.message.reply_document(
                            document=pdf_file,
                            filename="Сгенерированный_договор.pdf",
                            caption="✅ Договор от нейросети!"
                        )
                    os.unlink(pdf_path)
                else:
                    await update.message.reply_text(f"📝 Вот что получилось:\n\n{answer}")
                    
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await update.message.reply_text("❌ Ошибка, попробуй позже.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Команды:\n"
        "/start - приветствие\n"
        "/help - помощь\n\n"
        "Напиши: аренда, купля, услуги - получишь PDF"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
