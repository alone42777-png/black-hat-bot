import datetime
import time
from telebot import types
from database import db, log_user, add_credit, spend_credit, is_simple_admin, redeem_gift
from config import FORCE_CHANNEL, ADMIN_ID
from telebot.apihelper import ApiTelegramException

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
        is_new = log_user(message)
        if message.from_user.id != ADMIN_ID and not is_subscribed(bot, message.from_user.id):
            markup = types.InlineKeyboardMarkup()
            url = f"https://t.me/{FORCE_CHANNEL.replace('@', '')}"
            markup.add(types.InlineKeyboardButton("📢 جۆینبوون بە کەناڵ", url=url))
            return bot.send_message(message.chat.id, "⚠️ تکایە سەرەتا جۆین بە کەناڵەکە ببە!", reply_markup=markup)
            
        if is_new:
            add_credit(message.from_user.id, 5)
            bot.send_message(message.chat.id, "🎁 <b>پیرۆزە!</b> وەک دیاری یەکەم جار، <b>5 کرێدیت</b> بەخۆڕایی زیادکرا.")
            
        bot.send_message(message.chat.id, "💀 <b>BLACK HAT AI PRIME CORE</b> 💀\n\nسیستەمەکە ئامادەیە.\n🌐 وێنە بنێرە یان پرسیار بکە.")

    @bot.message_handler(commands=["credit"])
    def cmd_credit(message):
        if is_simple_admin(message.from_user.id) or message.from_user.id == ADMIN_ID:
            return bot.reply_to(message, "💳 کرێدیت: <b>♾️ بێکۆتایی</b>")
        row = db().execute("SELECT questions_left FROM credit WHERE user_id=?", (message.from_user.id,)).fetchone()
        bot.reply_to(message, f"💳 کرێدیت: <b>{row[0] if row else 0}</b>")

    @bot.message_handler(commands=["daily"])
    def cmd_daily(message):
        log_user(message)
        uid = message.from_user.id
        if is_simple_admin(uid) or uid == ADMIN_ID:
            return bot.reply_to(message, "💳 تۆ ئەدمینیت، پێویست بە کرێدیتی ڕۆژانە ناکات.")

        row = db().execute("SELECT last_daily FROM users WHERE user_id=?", (uid,)).fetchone()
        now = time.time()
        if row and row[0]:
            try:
                last_daily = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").timestamp()
                if now - last_daily < 86400:
                    rem = 86400 - int(now - last_daily)
                    return bot.reply_to(message, f"⏳ چاوەڕوان بە. <b>{rem // 3600}</b> کاتژمێر و <b>{(rem % 3600) // 60}</b> خولەک ماوە.")
            except ValueError: pass

        add_credit(uid, 1)
        db().execute("UPDATE users SET last_daily=datetime('now', 'localtime') WHERE user_id=?", (uid,))
        db().commit()
        bot.reply_to(message, "🎁 <b>پیرۆزە!</b> 1 کرێدیتی ڕۆژانە وەرگیرا.")

    @bot.message_handler(commands=["gift"])
    def cmd_gift(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2: return bot.reply_to(message, "🎁 کۆدەکە بنووسە.")
        ok, reason, reward = redeem_gift(message.from_user.id, parts[1])
        if ok: bot.reply_to(message, f"🎉 پیرۆزە! {reward} کرێدیت زیادکرا.")
        else: bot.reply_to(message, f"❌ {reason}")
