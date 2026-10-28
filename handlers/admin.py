from database import db, get_setting, set_setting
from config import ADMIN_ID

def register(bot):
    @bot.message_handler(commands=["panel"])
    def cmd_panel(message):
        if message.from_user.id != ADMIN_ID: return
        total_users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
        bot.send_message(message.chat.id, f"👑 <b>پەنێلی ئەدمین</b>\n\n👥 بەکارهێنەران: {total_users}")
