import logging
import telebot
from config import TOKEN
from database import init_db
from handlers import user, admin, ai_chat # لێرە هەموو فایلەکانی تر import دەکرێن

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Core")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# بانگکردنی هەموو فایلەکان
init_db()
user.register(bot)
admin.register(bot)
ai_chat.register(bot) # ئەمە فایلی وەڵامدانەوەی AIیە کە دەبێت دروستی بکەیت

if __name__ == "__main__":
    logger.info("Bot started successfully. absolute olliE.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
