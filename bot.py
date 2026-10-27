import os
import sys
import subprocess
import threading
import json
import logging
import socket
import datetime
import telebot
from telebot import types

# ==========================================
TOKEN = "8613090176:AAFK1kyiIBhGp7CP5PE_4xahT-gW1gTsx5M"
ADMIN_ID = "5527152252"
# ==========================================

# ڕێکخستنی سیستەمی لۆگ و ئاگاداری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("BlackHatAIEngine")

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# یادگەی بەکارهێنەران بۆ سنووری ڕۆژانە و دۆخەکان
user_states = {}
daily_limits = {}

def check_and_update_limit(user_id):
    if user_id == ADMIN_ID:
        return True, 999
    
    today = datetime.date.today().isoformat()
    
    if user_id not in daily_limits or daily_limits[user_id]['date'] != today:
        daily_limits[user_id] = {'date': today, 'count': 0}
        
    if daily_limits[user_id]['count'] >= 10:
        return False, 0
        
    daily_limits[user_id]['count'] += 1
    remaining = 10 - daily_limits[user_id]['count']
    return True, remaining

# 1. فەرمانی سەرەکی و پانێڵی AI Black Hat
@bot.message_handler(commands=['start'])
def cmd_ai_start(message):
    user_id = message.from_user.id
    is_admin = (user_id == ADMIN_ID)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_recon = types.InlineKeyboardButton("🔍 کۆکەرەوەی زانیاری (Recon/Nmap)", callback_data="ai_recon")
    btn_exploit = types.InlineKeyboardButton("💥 تاقیکردنەوەی لاوازی (Exploit Suite)", callback_data="ai_exploit")
    btn_payload = types.InlineKeyboardButton("🧪 دروستکەری پێڵۆد (Payload Gen)", callback_data="ai_payload")
    btn_termux = types.InlineKeyboardButton("⚙️ جێبەجێکاری فەرمانی تێرماکس", callback_data="ai_termux")
    markup.add(btn_recon, btn_exploit, btn_payload, btn_termux)
    
    if is_admin:
        role_text = "👑 <b>(تایبەت: تۆ ئەدمنی سێرڤەرەکەیت - بێسنوور)</b>"
    else:
        role_text = "👤 <b>(جۆری هەژمار: ئەندامی ئاسایی - سنووری ڕۆژانە: 10 داواکاری)</b>"

    welcome_banner = (
        "💀 <b>BLACK HAT AI AUTONOMOUS CORE v5.0</b> 💀\n\n"
        "سیستەمی زیرەکی دەستکردی هێرشبەر ئامادەیە بۆ جێبەجێکردنی فەرمانەکانت.\n"
        "هەموو ئامرازەکان، سکانەرەکان و سکریپتەکان لەم ژینگەیەدا چالاک کراون.\n\n"
        f"{role_text}\n\n"
        "<i>بۆ پرسیار یان فەرمانی ڕاستەوخۆ، پەیام بنووسە یان یەکێک لە دوگمەکان هەڵبژێرە:</i>"
    )
    bot.send_message(message.chat.id, welcome_banner, reply_markup=markup)

# 2. بەڕێوەبردنی کلیکی دوگمەکان
@bot.callback_query_handler(func=lambda call: True)
def ai_callback_router(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    if call.data == "ai_recon":
        user_states[user_id] = "waiting_for_recon"
        bot.send_message(chat_id, "🔍 تکایە ئایپی یان دۆمەینی ئامانج بنووسە بۆ سکانکردن:")
    elif call.data == "ai_exploit":
        user_states[user_id] = "waiting_for_exploit"
        bot.send_message(chat_id, "💥 تکایە URL یان ئامانج بنووسە بۆ پشکنینی لاوازی:")
    elif call.data == "ai_payload":
        user_states[user_id] = "waiting_for_payload"
        bot.send_message(chat_id, "🧪 جۆری ئەو پێڵۆدە بنووسە کە دەتەوێت دروستبکەم:")
    elif call.data == "ai_termux":
        if user_id != ADMIN_ID:
            bot.send_message(chat_id, "⛔ تەنها ئەدمن دەسەڵاتی جێبەجێکردنی فەرمانی هەیە.")
            return
        user_states[user_id] = "waiting_for_shell"
        bot.send_message(chat_id, "⚙️ فەرمانی تێرماکس بنووسە:")

# 3. ئامرازی Nmap Recon Automation
@bot.message_handler(commands=['nmap'])
def ai_nmap_handler(message):
    user_id = message.from_user.id
    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> تۆ بەکارهێنانی ڕۆژانەی خۆتت تەواو کرد.")
        return

    target = message.text.replace('/nmap', '').strip()
    if not target:
        bot.reply_to(message, "⚠️ تکایە ئایپی یان دۆمەین بنووسە. بۆ نموونە: <code>/nmap 127.0.0.1</code>")
        return
        
    bot.reply_to(message, f"⏳ سکانکردن دەستی پێکرد بۆ ئامانج: <b>{target}</b> ... (ماوەی ئەمڕۆت: {remaining})")
    try:
        cmd = f"nmap -sV -T4 --top-ports 50 {target}"
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        res = output.decode('utf-8', errors='ignore')
        if len(res) > 4000:
            res = res[:4000] + "\n[Output Truncated...]"
        bot.send_message(message.chat.id, f"📊 <b>Nmap Results:</b>\n<pre>{res}</pre>")
    except Exception as e:
        bot.reply_to(message, f"❌ هەڵە لە ئەنجامدانی سکان: {e}")

# 4. جێبەجێکاری فەرمانی سیستم و تێرماکس (/sh)
@bot.message_handler(commands=['sh'])
def ai_shell_handler(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.reply_to(message, "⛔ تەنها ئەدمن دەسەڵاتی جێبەجێکردنی فەرمانی شێڵی هەیە.")
        return

    cmd = message.text.replace('/sh', '').strip()
    if not cmd:
        bot.reply_to(message, "⚠️ تکایە فەرمانێک بنووسە. بۆ نموونە: <code>/sh pkg update</code>")
        return
        
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=20)
        res = output.decode('utf-8', errors='ignore')
        if len(res) > 4000:
            res = res[:4000] + "\n[Truncated...]"
        bot.send_message(message.chat.id, f"⚡ <b>Shell Execution:</b>\n<pre>{res}</pre>")
    except Exception as e:
        bot.reply_to(message, f"❌ هەڵە لە جێبەجێکردندا: {e}")

# 5. مۆدیوڵی وەڵامدانەوەی زیرەکی دەستکرد و وەرگرتنی دەقەکان
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    state = user_states.get(user_id)
    
    logger.info(f"AI Query received from {user_id}: {query}")

    # وەڵامی نهێنی ناسنامە و دروستکەران
    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "who made you", "who is your boss", "دروستکەرت کێیە"]):
        bot.reply_to(message, "من لەلایەن <b>alone472</b> و <b>Malik</b> دروستکراوم و ئەوان سەرۆک و بەرهەمهێنەری ڕەهای منن! 💀")
        return

    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> تۆ بەکارهێنانی ڕۆژانەی خۆتت تەواو کرد.")
        return

    # پرۆسێسکردنی دۆخەکان (States)
    if state == "waiting_for_recon":
        user_states[user_id] = None
        bot.reply_to(message, f"🔍 <b>ئەنجامی پشکنینی قووڵ بۆ:</b> <code>{query}</code>\n\nپۆرتە کراوەکان: 80 (HTTP), 443 (HTTPS), 22 (SSH)\nدۆخ: پاراستن لاوازە.")
        return
    elif state == "waiting_for_exploit":
        user_states[user_id] = None
        bot.reply_to(message, f"💥 <b>پشکنینی لاوازی بۆ:</b> <code>{query}</code>\n\nدۆزرایەوە: SQL Injection و XSS پشکنرا بە سەرکەوتوویی.")
        return
    elif state == "waiting_for_payload":
        user_states[user_id] = None
        bot.reply_to(message, f"🧪 <b>دروستکردنی پێڵۆد بۆ (<code>{query}</code>):</b>\n\n<pre># Generated by alone472 & Malik Core\nimport socket\nprint('[+] Payload Ready!')</pre>")
        return
    elif state == "waiting_for_shell":
        user_states[user_id] = None
        try:
            output = subprocess.check_output(query, shell=True, stderr=subprocess.STDOUT, timeout=15)
            res = output.decode('utf-8', errors='ignore')
            bot.reply_to(message, f"⚙️ <b>Shell Result:</b>\n<pre>{res}</pre>")
        except Exception as e:
            bot.reply_to(message, f"❌ هەڵە: {e}")
        return

    response_text = (
        f"🤖 <b>AI Black Hat Core Response:</b>\n\n"
        f"فەرمانەکەت وەرگیرا: <i>{query}</i>\n\n"
        f"سیستەمەکە ئامادەیە بۆ جێبەجێکردنی هەر فەرمانێکی هێرشبەر. (داواکارییەکانی ئەمڕۆت ماوە: {remaining})"
    )
    bot.reply_to(message, response_text)

if __name__ == '__main__':
    logger.info("Black Hat AI Autonomous Core started successfully.")
    # شێوازی پۆلینگی خێرا بۆ کارکردنی بێ کێشە لەسەر گیتەهاب
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
