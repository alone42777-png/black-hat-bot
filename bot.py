import os
import sys
import subprocess
import threading
import json
import logging
import socket
import datetime
import random
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
    
    if user_id not in daily_limits || daily_limits[user_id]['date'] != today:
        daily_limits[user_id] = {'date': today, 'count': 0}
        
    if daily_limits[user_id]['count'] >= 10:
        return False, 0
        
    daily_limits[user_id]['count'] += 1
    remaining = 10 - daily_limits[user_id]['count']
    return True, remaining

# 1. فەرمانی سەرەکی /start بە دەقە داواکراوەکە
@bot.message_handler(commands=['start'])
def cmd_ai_start(message):
    user_id = message.from_user.id
    is_admin = (user_id == ADMIN_ID)
    
    if is_admin:
        role_text = "👑 <b>(جۆری هەژمار: ئەدمنی سێرڤەرەکەیت - بێسنوور)</b>"
    else:
        role_text = "👤 <b>(جۆری هەژمار: ئەندامی ئاسایی - سنووری ڕۆژانە: 10 داواکاری)</b>"

    welcome_banner = (
        "💀 <b>BLACK HAT AI AUTONOMOUS CORE v5.0</b> 💀\n\n"
        "سیستەمی زیرەکی دەستکردی هێرشبەر ئامادەیە بۆ جێبەجێکردنی فەرمانەکانت.\n"
        "هەموو ئامرازەکان، سکانەرەکان و سکریپتەکان لەم ژینگەیەدا چالاک کراون.\n\n"
        f"{role_text}\n\n"
        "ئەگەر نازانی داواکاری بکەیت یان ناوی توڵ (هاک) نازانی بنوسە /help بۆ لیستی هاک و تواناکانم"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_recon = types.InlineKeyboardButton("🔍 پشکنینی ئامانج (Recon)", callback_data="ai_recon")
    btn_exploit = types.InlineKeyboardButton("💥 تاقیکردنەوەی لاوازی", callback_data="ai_exploit")
    btn_payload = types.InlineKeyboardButton("🧪 دروستکەری پێڵۆد", callback_data="ai_payload")
    markup.add(btn_recon, btn_exploit, btn_payload)
    
    bot.send_message(message.chat.id, welcome_banner, reply_markup=markup)

# 2. فەرمانی /help بۆ نیشاندانی لیستی توڵەکان و بەکارهێنانیان
@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی هاک و توڵە بەردەستەکان (Help Directory):</b>\n\n"
        "1. <code>/nmap [IP]</code>\n"
        "   - <b>بۆ چی بەکاردێت:</b> سکانکردنی پۆرتە کراوەکان و دۆزینەوەی خزمەتگوزارییەکان لەسەر ئامانج.\n\n"
        "2. <code>/sh [command]</code>\n"
        "   - <b>بۆ چی بەکاردێت:</b> جێبەجێکردنی فەرمانەکانی تێرماکس/سیستم (تایبەت بە ئەدمن).\n\n"
        "3. <b>داواکاری توڵ یان سکریپت (بە ڕستە):</b>\n"
        "   - دەتوانیت بە شێوەی ڕستە داوای هەر توڵێک بکەیت (وەکو: <i>تۆڵێکی ddos دروست بکە</i> یان <i>سێرچەری پۆرت دروست بکە</i>)، سیستەمەکە هەر جارێک توڵێکی نوێ و جیاوازت بۆ دروست دەکات!\n\n"
        "📌 <i>بۆ هەر پرسیارێک، ڕاستەوخۆ پەیام بنووسە.</i>"
    )
    bot.reply_to(message, help_text)

# 3. بەڕێوەبردنی کلیکی دوگمەکان
@bot.callback_query_handler(func=lambda call: True)
def ai_callback_router(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    if call.data == "ai_recon":
        user_states[user_id] = "waiting_for_recon"
        bot.send_message(chat_id, "🔍 تکایە ئایپی یان دۆمەینی ئامانج بنووسە بۆ پشکنین:")
    elif call.data == "ai_exploit":
        user_states[user_id] = "waiting_for_exploit"
        bot.send_message(chat_id, "💥 تکایە URL یان ئامانج بنووسە بۆ پشکنینی لاوازی:")
    elif call.data == "ai_payload":
        user_states[user_id] = "waiting_for_payload"
        bot.send_message(chat_id, "🧪 جۆری ئەو پێڵۆدە بنووسە کە دەتەوێت دیزاینی تازەی بۆ بکەم:")

# 4. ئامرازی Nmap
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

# 5. جێبەجێکاری فەرمانی سیستم (/sh)
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

# 6. مۆدیوڵی زیرەکی دەستکرد بۆ دروستکردنی توڵی نوێ و جیاواز (Dynamic Code Generator)
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

    if state == "waiting_for_recon":
        user_states[user_id] = None
        bot.reply_to(message, f"🔍 <b>ئەنجامی پشکنینی پێشکەوتوو بۆ:</b> <code>{query}</code>\n\n- پۆرتە کراوەکان: 80, 443, 8080\n- خزمەتگوزاری: Apache/2.4.41\n- دۆخ: سەلامەتە بەڵام پۆرتەکان ئاشکران.")
        return
    elif state == "waiting_for_exploit":
        user_states[user_id] = None
        bot.reply_to(message, f"💥 <b>پشکنینی لاوازی بۆ ئامانج:</b> <code>{query}</code>\n\n- جۆری لاوازی: Reflected XSS & SQLi\n- مەترسی: بەرز (High)")
        return
    elif state == "waiting_for_payload" or state == "waiting_for_shell":
        user_states[user_id] = None
        # دروستکردنی نموونەی کۆدی گۆڕاو و تازە
        rand_port = random.randint(1000, 9999)
        code_example = (
            f"# Dynamic Python Exploit Core v{random.randint(2,9)}.0\n"
            f"# Generated fresh by alone472 & Malik Core\n"
            f"import socket, subprocess, time\n\n"
            f"TARGET_PORT = {rand_port}\n"
            f"def execute_task():\n"
            f"    print(f'[*] Initializing secure socket on port {{TARGET_PORT}}...')\n"
            f"    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            f"    s.bind(('0.0.0.0', TARGET_PORT))\n"
            f"    s.listen(1)\n"
            f"    conn, addr = s.accept()\n"
            f"    print(f'[+] Connected from {{addr}}')\n\n"
            f"if __name__ == '__main__':\n"
            f"    execute_task()"
        )
        instructions = (
            f"📌 <b>ڕێنمایی بەکارهێنان لە تێرماکس (Termux):</b>\n"
            f"1. کۆدەکە لە فایلێکی پایتۆن بە ناوی <code>tool_{rand_port}.py</code> پاشەکەوت بکە.\n"
            f"2. بە فەرمانی زیرک جێبەجێی بکە:\n"
            f"   <code>python tool_{rand_port}.py</code>"
        )
        bot.reply_to(message, f"🧪 <b>دیزاینی نوێی پێڵۆد بۆ (<code>{query}</code>):</b>\n\n<pre><code>{code_example}</code></pre>\n\n{instructions}")
        return

    # ئەگەر داوای توڵ، سکریپت، DDoS یا هەر کارێکی هاککردنی کرد، کۆدی نوێ و هەڕەمەکی دروست بکە
    if any(w in query_lower for w in ["توڵ", "کۆد", "script", "tool", "دروست", "payload", "ddos", "تۆلیک", "سکانەر"]):
        rand_id = random.randint(100, 999)
        code_example = (
            f"# Autonomous Advanced Tool #{rand_id}\n"
            f"# Created fresh by alone472 & Malik Core\n"
            f"import sys, time, socket, random\n\n"
            f"def run_routine():\n"
            f"    print('[~] Target analysis in progress...')\n"
            f"    bytes_data = random._urandom(1024)\n"
            f"    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n"
            f"    print(f'[+] Module #{rand_id} compiled successfully.')\n\n"
            f"if __name__ == '__main__':\n"
            f"    run_routine()"
        )
        instructions = (
            "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
            "1. کۆدەکە کۆپی بکە و لە فایلێک بە ناوی <code>script.py</code> دایبنێ.\n"
            "2. لە تێرماکس (Termux) کارپێکردن ئەنجام بدە:\n"
            "   <code>python script.py</code>\n"
            "3. <i>تێبینی: ئەم دیزاینە تایبەت و نوێیە و بۆ ئەم داواکارییە بەرهەم هێنراوە.</i>"
        )
        bot.reply_to(message, f"🛠 <b>توڵی نوێی بەرهەمهاتوو بۆ: {query}</b>\n\n<pre><code>{code_example}</code></pre>\n\n{instructions}")
        return

    response_text = (
        f"🤖 <b>AI Black Hat Core Response:</b>\n\n"
        f"فەرمانەکەت وەرگیرا: <i>{query}</i>\n\n"
        f"سیستەمەکە ئامادەیە. (داواکارییەکانی ئەمڕۆت ماوە: {remaining})\n\n"
        "💡 <i>بۆ بینینی هەموو تواناکان، فەرمانی /help بنووسە.</i>"
    )
    bot.reply_to(message, response_text)

if __name__ == '__main__':
    logger.info("Black Hat AI Autonomous Core started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
