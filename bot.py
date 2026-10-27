import os
import sys
import subprocess
import threading
import json
import logging
import socket
import telebot
from telebot import types

# ڕێکخستنی سیستەمی لۆگ و ئاگاداری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("BlackHatAIEngine")

TOKEN = os.environ.get('BOT_TOKEN', '8814964477:AAHNn3tNITZarQhxyYciS-AKfmXXsyODSN4')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '5527152252'))

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# 1. کتێبخانەی ئامرازە خۆکارەکان (Automated Tool Generator & Runner)
TOOLS_REGISTRY = {
    "nmap_scan": "nmap -sV -T4 --top-ports 100",
    "sql_inject": "sqlmap --batch --random-agent --dbs -u",
    "dir_buster": "gobuster dir -u",
    "hydra_brute": "hydra -l admin -P wordlist.txt",
    "git_clone": "git clone"
}

# 2. فەرمانی سەرەکی و پانێڵی AI Black Hat
@bot.message_handler(commands=['start'])
def cmd_ai_start(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Access Denied. Autonomous AI Core is locked.")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_recon = types.InlineKeyboardButton("🔍 کۆکەرەوەی زانیاری (Recon/Nmap)", callback_data="ai_recon")
    btn_exploit = types.InlineKeyboardButton("💥 تاقیکردنەوەی لاوازی (Exploit Suite)", callback_data="ai_exploit")
    btn_payload = types.InlineKeyboardButton("🧪 دروستکەری پێڵۆد (Payload Gen)", callback_data="ai_payload")
    btn_termux = types.InlineKeyboardButton("⚙️ جێبەجێکاری فەرمانی تێرماکس", callback_data="ai_termux")
    markup.add(btn_recon, btn_exploit, btn_payload, btn_termux)
    
    welcome_banner = (
        "💀 <b>BLACK HAT AI AUTONOMOUS CORE v5.0</b> 💀\n\n"
        "سیستەمی زیرەکی دەستکردی هێرشبەر ئامادەیە بۆ جێبەجێکردنی فەرمانەکانت.\n"
        "هەموو ئامرازەکان، سکانەرەکان و سکریپتەکان لەم ژینگەیەدا چالاک کراون.\n\n"
        "<i>بۆ پرسیار یان فەرمانی ڕاستەوخۆ، پەیام بنووسە یان یەکێک لە دوگمەکان هەڵبژێرە:</i>"
    )
    bot.send_message(message.chat.id, welcome_banner, reply_markup=markup)

# 3. بەڕێوەبردنی کلیکی دوگمەکان و وەڵامی زیرەک
@bot.callback_query_handler(func=lambda call: True)
def ai_callback_router(call):
    if call.from_user.id != ADMIN_ID:
        return
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    
    if call.data == "ai_recon":
        bot.send_message(chat_id, "🔍 بۆ ئەنجامدانی سکانی پێشکەوتوو، ئەم فەرمانە بنووسە:\n<code>/nmap target_ip</code>")
    elif call.data == "ai_exploit":
        bot.send_message(chat_id, "💥 بۆ پشکنینی SQL Injection، ئەم فەرمانە بنووسە:\n<code>/sql target_url</code>")
    elif call.data == "ai_payload":
        bot.send_message(chat_id, "🧪 بۆ دروستکردنی پێڵۆدی مۆبایل/سیستم، /payload [msfvenom/python] بنووسە.")
    elif call.data == "ai_termux":
        bot.send_message(chat_id, "⚙️ بۆ جێبەجێکردنی هەر فەرمانێکی تێرماکس، /sh [command] بنووسە.")

# 4. ئامرازی Nmap Recon Automation
@bot.message_handler(commands=['nmap'])
def ai_nmap_handler(message):
    if message.from_user.id != ADMIN_ID:
        return
    target = message.text.replace('/nmap', '').strip()
    if not target:
        bot.reply_to(message, "⚠️ تکایە ئایپی یان دۆمەین بنووسە. بۆ نموونە: <code>/nmap 127.0.0.1</code>")
        return
        
    bot.reply_to(message, f"⏳ سکانکردن دەستی پێکرد بۆ ئامانج: <b>{target}</b> ...")
    try:
        cmd = f"nmap -sV -T4 --top-ports 50 {target}"
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        res = output.decode('utf-8', errors='ignore')
        if len(res) > 4000:
            res = res[:4000] + "\n[Output Truncated...]"
        bot.send_message(message.chat.id, f"📊 <b>Nmap Results:</b>\n<pre>{res}</pre>")
    except Exception as e:
        bot.reply_to(message, f"❌ هەڵە لە ئەنجامدانی سکان: {e}")

# 5. جێبەجێکاری فەرمانی سیستم و تێرماکس بە شێوەی ڕەها (/sh)
@bot.message_handler(commands=['sh'])
def ai_shell_handler(message):
    if message.from_user.id != ADMIN_ID:
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
        bot.reply_to(message, f"⚡ <b>Shell Execution:</b>\n<pre>{res}</pre>")
    except Exception as e:
        bot.reply_to(message, f"❌ هەڵە لە جێبەجێکردندا: {e}")

# 6. مۆدیوڵی وەڵامدانەوەی زیرەکی دەستکرد بۆ هەر پرسیارێکی هاککردن (AI Prompt Handler)
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    if message.from_user.id != ADMIN_ID:
        return
        
    query = message.text.lower()
    logger.info(f"AI Query received: {query}")
    
    # وەڵامدەرەوەی زیرەک بۆ ڕێنمایی هەکراتی و دروستکردنی سکریپت
    response_text = (
        f"🤖 <b>AI Black Hat Core Response:</b>\n\n"
        f"فەرمانەکەت وەرگیرا: <i>{message.text}</i>\n\n"
        f"بۆ جێبەجێکردنی ئەم جۆرە ئەرکە، دەتوانیت فەرمانی ڕاستەوخۆ بەکاربهێنیت یان لەڕێگەی `/sh` سکریپتەکە لە تێرماکس یان سێرڤەرەکەدا بخەیتە کار.\n"
        f"سیستەمەکە ئامادەیە بۆ ئۆتۆماتیککردنی هەر کارێکی تری هێرشبەر."
    )
    bot.reply_to(message, response_text)

if __name__ == '__main__':
    logger.info("Black Hat AI Autonomous Core started successfully.")
    bot.infinity_polling()
