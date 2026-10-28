from telebot import types
from database import db, log_user, add_credit, spend_credit
from config import FORCE_CHANNEL, ADMIN_ID
from telebot.apihelper import ApiTelegramException
import datetime

def is_subscribed(bot, user_id):
    try:
        member = bot.get_chat_member(FORCE_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member']: return True
    except ApiTelegramException: return False
    except Exception: return False
    return False

def register(bot):
    @bot.message_handler(commands=["start"])
    def cmd_start(message):
        log_user(message)
        if message.from_user.id != ADMIN_ID and not is_subscribed(bot, message.from_user.id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 جۆینبوون بە کەناڵ", url=f"https://t.me/{FORCE_CHANNEL.replace('@', '')}"))
            return bot.send_message(message.chat.id, "⚠️ تکایە سەرەتا جۆین بە کەناڵەکە ببە!", reply_markup=markup)
            
        bot.send_message(message.chat.id, "💀 <b>BLACK HAT AI PRIME CORE v76.0</b> 💀\n\nسیستەمەکە بە تەواوی نوێ کرایەوە.\n🌐 وێنە بنێرە یان پرسیار بکە.")
