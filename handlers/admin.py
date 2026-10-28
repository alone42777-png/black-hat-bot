from database import db, get_setting, set_setting, add_credit, remove_credit, set_credit, create_gift, parse_ban_time
from config import ADMIN_ID
import time

def register(bot):
    @bot.message_handler(commands=["panel"])
    def cmd_panel(message):
        if message.from_user.id != ADMIN_ID: return
        total_users = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_simple = db().execute("SELECT COUNT(*) FROM simple_admins").fetchone()[0]
        text = (
            f"👑 <b>پەنێلی سەرۆکایەتی</b>\n\n"
            f"👥 بەکارهێنەران: {total_users}\n"
            f"⭐ ئەدمینی سادە: {total_simple}\n\n"
            f"📌 <b>فەرمانەکان:</b>\n"
            f"🔹 <code>/addsimple [ID]</code> — ئەدمینی سادە\n"
            f"🔹 <code>/removesimple [ID]</code> — لابردن\n"
            f"🔹 <code>/addcredit [ID] [ژمارە]</code> — زیادکردن\n"
            f"🔹 <code>/gen [ژمارە]</code> — کۆدی خەڵات\n"
            f"🔹 <code>/broadcast [نامە]</code> — نامە بۆ هەمووان"
        )
        bot.send_message(message.chat.id, text)

    @bot.message_handler(commands=["addsimple"])
    def cmd_add_simple(message):
        if message.from_user.id != ADMIN_ID: return
        parts = message.text.split()
        if len(parts) < 2: return bot.reply_to(message, "⚠️ نموونە: <code>/addsimple 123456789</code>")
        db().execute("INSERT OR IGNORE INTO simple_admins(user_id) VALUES(?)", (int(parts[1]),))
        db().commit()
        bot.reply_to(message, f"✅ بەکارهێنەر <code>{parts[1]}</code> کرا بە ئەدمینی سادە.")

    @bot.message_handler(commands=["removesimple"])
    def cmd_remove_simple(message):
        if message.from_user.id != ADMIN_ID: return
        parts = message.text.split()
        if len(parts) < 2: return
        db().execute("DELETE FROM simple_admins WHERE user_id=?", (int(parts[1]),))
        db().commit()
        bot.reply_to(message, f"✅ ئەدمینی سادە لابرا.")

    @bot.message_handler(commands=["addcredit"])
    def cmd_add_credit(message):
        if message.from_user.id != ADMIN_ID: return
        p = message.text.split()
        if len(p) < 3: return
        add_credit(int(p[1]), int(p[2]))
        bot.reply_to(message, f"✅ {p[2]} کرێدیت زیادکرا.")

    @bot.message_handler(commands=["gen"])
    def cmd_gen(message):
        if message.from_user.id != ADMIN_ID: return
        p = message.text.split()
        rew = int(p[1]) if len(p) > 1 and p[1].isdigit() else 10
        c = create_gift(rew)
        bot.reply_to(message, f"✅ کۆد: <code>{c}</code>")

    @bot.message_handler(commands=["broadcast"])
    def cmd_broadcast(message):
        if message.from_user.id != ADMIN_ID: return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2: return
        users = db().execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
        s, f = 0, 0
        for (uid,) in users:
            try:
                bot.send_message(uid, parts[1])
                s += 1
                time.sleep(0.05)
            except: f += 1
        bot.reply_to(message, f"✅ نێردرا: {s} | ❌ شکست: {f}")
