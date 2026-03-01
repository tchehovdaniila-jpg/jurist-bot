import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(astime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токены из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')

# Проверяем, что токены есть
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not SILICONFLOW_API_KEY:
    raise ValueError("SILICONFLOW_API_KEY не найден в переменных окружения")

# URL для SiliconFlow API (используем модель DeepSeek-R1, которая хорошо понимает русский)
API_URL = "https://api.siliconflow.com/v1/chat/completions"

# Словарь с шаблонами договоров
TEMPLATES = {
    "аренда": "Договор аренды квартиры\n\nАрендодатель: {арендодатель}\nАрендатор: {арендатор}\nАдрес: {адрес}\nСумма: {сумма} руб.\nСрок: {срок}",
    "купля": "Договор купли-продажи\n\nПродавец: {продавец}\nПокупатель: {покупатель}\nТовар: {товар}\nЦена: {цена} руб.",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    await update.message.reply_text(
        "👋 Привет! Я бот для создания договоров.\n"
        "Напиши, какой договор тебе нужен (например: 'аренда', 'купля')\n"
        "Или просто опиши ситуацию, и я помогу."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений"""
    user_message = update.message.text.lower()
    
    # Проверяем, есть ли готовый шаблон
    if "аренда" in user_message or "снять" in user_message or "квартир" in user_message:
        template = TEMPLATES.get("аренда", "Шаблон не найден")
        await update.message.reply_text(
            f"📄 Нашёл шаблон договора аренды:\n\n{template}\n\n"
            "Пришли данные в формате:\n"
            "арендодатель: Иван Петров\n"
            "арендатор: Сергей Сидоров\n"
            "адрес: Москва, ул. Ленина 1\n"
            "сумма: 30000\n"
            "срок: 11 месяцев"
        )
        return
    
    elif "купля" in user_message or "продаж" in user_message or "купить" in user_message:
        template = TEMPLATES.get("купля", "Шаблон не найден")
        await update.message.reply_text(
            f"📄 Нашёл шаблон договора купли-продажи:\n\n{template}\n\n"
            "Пришли данные в формате:\n"
            "продавец: ООО \"Ромашка\"\n"
            "покупатель: ИП Петров\n"
            "товар: Ноутбук\n"
            "цена: 50000"
        )
        return
    
    else:
        # Если нет шаблона, используем SiliconFlow
        await update.message.reply_text("⏳ Думаю над твоим договором...")
        
        try:
            # Подготовка запроса к SiliconFlow
            headers = {
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-ai/DeepSeek-R1",  # Хорошая модель для русского языка
                "messages": [
                    {"role": "system", "content": "Ты помощник, который составляет юридические договоры на русском языке. Отвечай кратко и по делу."},
                    {"role": "user", "content": f"Составь договор по запросу: {user_message}"}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            # Отправляем запрос
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(API_URL, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
            # Извлекаем ответ
            answer = result['choices'][0]['message']['content']
            await update.message.reply_text(f"📝 Вот что получилось:\n\n{answer}")
            
        except Exception as e:
            logger.error(f"Ошибка SiliconFlow: {e}")
            await update.message.reply_text("❌ Ошибка при обращении к нейросети. Попробуй позже.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    await update.message.reply_text(
        "📚 Доступные команды:\n"
        "/start - приветствие\n"
        "/help - эта справка\n\n"
        "Просто напиши, какой договор тебе нужен!"
    )

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
