import time
import os
from ai_core import get_prime_ai_response, get_vision_ai_response
from database import spend_credit, log_user, db
from config import ADMIN_ID

def get_signature():
    return (
        "\n\n───────────────────\n"
        "🛡 <b>[BLACK HAT AI PRIME CORE]</b>\n"
        "👑 <b>پەیوەندی:</b> @malikdlashad3 | @ALONE427"
    )

def register(bot):
    @bot.message_handler(content_types=["photo"])
    def handle_photo(message):
        log_user(message)
        if message.from_user.id != ADMIN_ID and not spend_credit(message.from_user.id):
            return bot.reply_to(message, "🔒 کرێدیتت نییە. بە <code>/daily</code> وەریبگرە.")
            
        bot.send_chat_action(message.chat.id, 'typing')
        msg = bot.reply_to(message, "👁 <b>سیستەمی بینین وێنەکە دەخوێنێتەوە...</b>")
        
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        with open("temp.jpg", 'wb') as new_file:
            new_file.write(downloaded)
            
        ai_res = get_vision_ai_response("temp.jpg", message.caption or "")
        safe_text = ai_res.replace('<', '&lt;').replace('>', '&gt;')
        res = f"<pre><code>{safe_text[:3800]}</code></pre>" + get_signature()
        
        try: 
            bot.edit_message_text(res, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
        except: 
            bot.send_message(message.chat.id, res)
            
        if os.path.exists("temp.jpg"): os.remove("temp.jpg")

    @bot.message_handler(func=lambda m: not m.text.startswith("/"), content_types=["text"])
    def handle_text(message):
        log_user(message)
        uid = message.from_user.id
        q = message.text.strip()
        ql = q.lower()

        if any(k in ql for k in ("کێ دروست", "who made you", "خاوەنی تۆ")):
            return bot.reply_to(message, "من لەلایەن @ALONE427 و @malikdlashad3 ـەوە دروستکراوم. 👑")
            
        if any(k in ql for k in ("سڵاو", "hello", "hi", "hey", "أهلا", "merhaba")):
            return bot.reply_to(message, "سڵاو بەخێربێیت بۆ سیستەمی ئاسایش و پڕۆگرامسازی. 🌐\nچۆن دەتوانم یارمەتیت بدەم؟" + get_signature())

        is_tool = any(w in ql for w in ("توڵ", "سکریپت", "payload", "پەیلوود", "exploit", "ddos", "دروست بکە", "کۆد", "tool", "script"))
        if is_tool and uid != ADMIN_ID and not spend_credit(uid):
            return bot.reply_to(message, "🔒 بۆ داواکاری توڵ/کۆد پێویستە کۆدی خەڵات بەکاربهێنە: <code>/gift [کۆد]</code>")

        bot.send_chat_action(message.chat.id, 'typing')
        msg = bot.reply_to(message, "🧠 <b>سیستەمی زیرەک شیکاری دەکات...</b>")
        
        ai_response = get_prime_ai_response(uid, q)
        safe_ai_text = ai_response.replace('<', '&lt;').replace('>', '&gt;')
        
        if len(safe_ai_text) > 3800:
            chunks = [safe_ai_text[i:i+3800] for i in range(0, len(safe_ai_text), 3800)]
            try:
                bot.edit_message_text(f"{chunks[0]}" + get_signature(), chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
            except:
                bot.send_message(message.chat.id, f"{chunks[0]}", parse_mode="HTML")
                
            for chunk in chunks[1:]:
                time.sleep(0.5)
                bot.send_message(message.chat.id, chunk, parse_mode="HTML")
        else:
            res = f"{safe_ai_text}" + get_signature()
            try:
                bot.edit_message_text(res, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
            except:
                bot.send_message(message.chat.id, res, parse_mode="HTML")
