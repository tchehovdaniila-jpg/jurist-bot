import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токены
BOT_TOKEN = os.environ.get('BOT_TOKEN')
SILICONFLOW_API_KEY = os.environ.get('SILICONFLOW_API_KEY')

# API SiliconFlow
API_URL = "https://api.siliconflow.com/v1/chat/completions"

# Простые шаблоны
TEMPLATES = {
    "аренда": "Договор аренды квартиры",
    "купля": "Договор купли-продажи"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я бот для договоров. Напиши 'аренда' или 'купля'.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    if "аренда" in text:
        await update.message.reply_text("📄 Шаблон аренды: нужны данные арендодателя, адрес, сумма")
    elif "купля" in text:
        await update.message.reply_text("📄 Шаблон купли-продажи: нужны данные продавца, товар, цена")
    else:
        await update.message.reply_text("🤖 Обращаюсь к нейросети...")
        
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
                await update.message.reply_text(f"📝 {answer}")
        except Exception as e:
            logger.error(e)
            await update.message.reply_text("❌ Ошибка, попробуй позже.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Команды: /start, /help")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
