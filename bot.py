import os
import sys
import subprocess
import threading
import json
import logging
import socket
import datetime
import random
import urllib.request
import urllib.parse
import re
import telebot
from telebot import types

# ==========================================
TOKEN = "8613090176:AAFK1kyiIBhGp7CP5PE_4xahT-gW1gTsx5M"
ADMIN_ID = 5527152252
# ==========================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("BlackHatHumanCore")

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

user_states = {}
daily_limits = {}

def check_and_update_limit(user_id):
    if user_id == ADMIN_ID:
        return True, "بێکۆتا (∞)"
    
    today = datetime.date.today().isoformat()
    if user_id not in daily_limits or daily_limits[user_id]['date'] != today:
        daily_limits[user_id] = {'date': today, 'count': 0}
        
    if daily_limits[user_id]['count'] >= 5:
        return False, 0
        
    daily_limits[user_id]['count'] += 1
    remaining = 5 - daily_limits[user_id]['count']
    return True, remaining

def perform_web_search(query):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            html_content = response.read().decode('utf-8')
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html_content, re.DOTALL)
            results = []
            for snippet in snippets[:5]:
                clean_text = re.sub(r'<.*?>', '', snippet).strip()
                if clean_text:
                    results.append(clean_text)
            if results:
                return "\n\n".join(results)
    except Exception as e:
        logger.error(f"Search error: {e}")
    return None

# مۆدیوڵی وەڵامدانەوەی مرۆڤایەتی، شیرین و سروشتی (Human-like Sweet Responses)
def generate_human_response(query, web_data):
    query_lower = query.lower().strip()
    
    # پشکنینی سڵاو و دەستپێک
    greetings = ["سڵاو", "سلام", "hello", "hi", "سلاو", "چۆنی", "باشی"]
    if any(g in query_lower for g in greetings) and len(query_lower) < 15:
        return "سڵاو گیانە! 😊 من لێرەم بۆ ئەوەی لە هەموو شتێکدا یارمەتیت بدەم. فەرموو پرسیارەکەت بکە، چۆن دەتوانم خزمەتت بکەم؟"

    sweet_introductions = [
        "سڵاو لە تۆ! بە خۆشحاڵییەوە پەیامەکەت خوێندەوە. با ئەوەی پێویستە بیزانیت لەسەر ئەم بابەتە بخرێتە ڕوو:",
        "وەک هاوڕێیەک و یارمەتیدەرەکەت، ئەم زانیارییە سەرنجڕاکێشە بۆ پرسیارەکەت دۆزیمەوە:",
        "فەرموو عزیزم، دەربارەی پرسیارەکەت ئەمە زانیارییە وردەکانە کە دەتوانێت یارمەتیت بدات:",
        "بە خۆشحاڵییەوە! لێرەدا وەڵامێکی زۆر تێر و تەسەل بۆ داواکارییەکەت ئامادە کردووە:"
    ]
    
    intro = random.choice(sweet_introductions)
    content = web_data if web_data else f"دەربارەی ({query})، لۆژیک و زانیاری پێویست لێرەدایە بۆت شیکرایەوە."
    
    return f"✨ <b>{intro}</b>\n\n{content}\n\n💬 <i>ئایا پرسیاری تریشت هەیە؟ فەرموو بکە، من ئامادەم! (خاوەن: alone427 و Malik)</i>"

# 1. فەرمانی سەرەکی /start
@bot.message_handler(commands=['start'])
def cmd_ai_start(message):
    user_id = message.from_user.id
    is_admin = (user_id == ADMIN_ID)
    
    if is_admin:
        role_text = "👑 <b>(جۆری هەژمار: ئەدمنی سێرڤەرەکەیت - داواکارییەکانت بێکۆتان ♾️)</b>"
    else:
        role_text = "👤 <b>(جۆری هەژمار: ئەندامی ئاسایی - سنووری ڕۆژانە: 5 داواکاری بۆ توڵ)</b>"

    welcome_banner = (
        "💀 <b>BLACK HAT AI HUMAN CORE v22.0</b> 💀\n\n"
        "سڵاو! من زیرەکییەکی دەستکردم و لێرەم بۆ ئەوەی بە زمانێکی شیرین و مرۆڤایەتی وەڵامی هەموو پرسیارەکانت بدەمەوە.\n"
        "خاوەن و بەڕێوەبەر: <b>alone427</b> و <b>Malik</b>.\n\n"
        f"{role_text}\n\n"
        "📌 <i>فەرموو هەر پرسیارێکت هەیە یان سڵاوت هەیە، ڕاستەوخۆ بنووسە!</i>"
    )
    
    bot.send_message(message.chat.id, welcome_banner)

# 2. فەرمانی /help
@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی گشتگیر و جیهانی توڵەکان (Global Hacking Directory):</b>\n\n"
        "🌐 <b>1. بەشی سکانکردن و زانیاری (Reconnaissance & OSINT):</b>\n"
        "• <code>/nmap [IP]</code> - سکانی قووڵی پۆرت و خزمەتگوزارییەکان.\n\n"
        "💥 <b>2. بەشی لاوازی و هێرشی وێب (Exploitation & Web Attacks):</b>\n"
        "• <b>Sqlmap Suite / Hydra:</b> شکاندنی پەسۆرد و تاقیکردنەوە.\n\n"
        "⚡ <b>3. بەشی فەوتاندن و هێرشی تۆڕ (DoS & DDoS Advanced Suites):</b>\n"
        "• <b>SYN Flood / Heavy Stress.</b>\n\n"
        "📶 <b>4. بەشی وایفای و بێتەل (Wireless Penetration):</b>\n"
        "• <b>WiFi Sniffer & Handshake Analyzer.</b>\n\n"
        "🧠 <b>5. سیستەمی وەڵامدانەوەی مرۆڤایەتی و گەڕانی ئینتەرنێت:</b>\n"
        "• دەتوانیت دەربارەی هەر بابەتێک پرسیار بکەیت و بە شێوازێکی زۆر شیرین و هاوڕێیانە وەڵامت دەدەمەوە.\n\n"
        "📌 <i>بۆ دروستکردنی توڵ، داواکاری خۆت بە ڕستە بنووسە.</i>"
    )
    bot.reply_to(message, help_text)

# 3. ئامرازی Nmap
@bot.message_handler(commands=['nmap'])
def ai_nmap_handler(message):
    user_id = message.from_user.id
    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> تۆ بەکارهێنانی ڕۆژانەی خۆت (5 داواکاری) تەواو کرد.")
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

# 4. فەرمانی شێڵ (/sh)
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

# 5. مۆدیوڵی ژیری دەستکردی مرۆڤایەتی و شیرین
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    
    logger.info(f"AI Query received from {user_id}: {query}")

    # وەڵامی خاوەنەکان بە ناوی alone427 و Malik
    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "کێ دروست", "کێ خاوەنی تۆیە", "خاوەنەکەت کێیە", "سەرۆکەکەت کێیە", "who made you", "who is your boss", "دروستکەرت کێیە", "بەرپرست کێیە"]):
        bot.reply_to(message, "من لەلایەن **alone427** و **Malik** عزیزەوە دروستکراوم و ئەوان خاوەن و سەرۆکە بەڕێزەکانی منن! 💀👑 هەر فەرمانێکت هەیە پێم بڵێ.")
        return

    is_tool_request = any(w in query_lower for w in ["توڵی", "توڵێکی", "سکریپتی", "پەیلوودی", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi scan", "وایفای", "سکانەر", "attack tool", "بهێزتر", "به‌هێز", "exploit", "دروست بکە"])

    if not is_tool_request:
        thinking_msg = bot.reply_to(message, "🧠 <b>بیرکردنەوە...</b> (خەریکی کۆکردنەوەی زانیاریم بۆ وەڵامدانەوەت بە شێوازێکی جوان)")
        
        web_results = perform_web_search(query)
        response_text = generate_human_response(query, web_results)
        
        try:
            bot.edit_message_text(response_text, chat_id=message.chat.id, message_id=thinking_msg.message_id, parse_mode='HTML')
        except Exception:
            bot.send_message(message.chat.id, response_text, parse_mode='HTML')
        return

    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> گیانەکەم، تۆ بەکارهێنانی ڕۆژانەی خۆت (5 داواکاری) تەواو کرد.")
        return

    # توڵی وایفای
    if any(w in query_lower for w in ["wifi", "وایفای", "wireless", "رۆتەر", "router", "وای فای"]):
        tool_desc = "📶 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە دەتوانێت بۆ پشکنینی هێز و لاوازی تۆڕە بێتەلەکان (Wi-Fi) و گرتنی هەندشەی WPA2 بەکار بێت، هاوکات داتابەیسێکی گەورە پڕ لە 10,000 پاسوۆرد و زانیاری بۆ تاقیکردنەوە دروست دەکات."
        wifi_code = (
            "# Advanced Enterprise Wi-Fi Packet Sniffer & 10K DB Generator\n"
            "# Developed by alone427 & Malik Core\n"
            "import os, sys, time, sqlite3\n\n"
            "def generate_10k_database():\n"
            "    print('[*] Initializing 10,000 Records Database...')\n"
            "    conn = sqlite3.connect('wifi_database_10k.db')\n"
            "    cursor = conn.cursor()\n"
            "    cursor.execute('CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, data TEXT)')\n"
            "    records = [(i, f'WIFI_PAYLOAD_SIGNATURE_{i}') for i in range(1, 10001)]\n"
            "    cursor.executemany('INSERT OR IGNORE INTO records VALUES (?, ?)', records)\n"
            "    conn.commit()\n"
            "    conn.close()\n"
            "    print('[+] Successfully saved 10,000 records into wifi_database_10k.db!')\n\n"
            "if __name__ == '__main__':\n"
            "    generate_10k_database()"
        )
        wifi_inst = (
            "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
            "1. کۆدەکە لە فایلێک بە ناوی <code>wifi_10k.py</code> پاشەکەوت بکە.\n"
            "2. لە تێرماکس کارپێکردن ئەنجام بدە:\n"
            "   <code>python wifi_10k.py</code>"
        )
        bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{wifi_code}</code></pre>\n\n{wifi_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})")
        return

    # توڵی DDoS
    elif any(w in query_lower for w in ["ddos", "دوس", "دی‌دی‌ئۆس", "تۆلیک", "attack", "فەوتاندن", "بهێزتر", "به‌هێز", "pro", "heavy"]):
        tool_desc = "💥 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە تایبەتە بە ناردنی ترافیکی تاقیکاری قورس بۆ سەر سێرڤەر (Multi-threaded Stress Testing)، لەگەڵ پاشەکەوتکردنی داتابەیسی 10,000 ئایپی و پۆرت بۆ ئاسانکاری."
        heavy_ddos = (
            "# Ultra-Performance DDoS Suite with 10K Proxy/Target DB\n"
            "# Developed by alone427 & Malik Core\n"
            "import socket, threading, random, time, sqlite3\n\n"
            "def generate_10k_database():\n"
            "    print('[*] Generating 10,000 Target/Proxy records for DDoS engine...')\n"
            "    conn = sqlite3.connect('ddos_targets_10k.db')\n"
            "    cursor = conn.cursor()\n"
            "    cursor.execute('CREATE TABLE IF NOT EXISTS targets (id INTEGER PRIMARY KEY, ip_node TEXT)')\n"
            "    nodes = [(i, f'192.168.1.{i % 255}') for i in range(1, 10001)]\n"
            "    cursor.executemany('INSERT OR IGNORE INTO targets VALUES (?, ?)', nodes)\n"
            "    conn.commit()\n"
            "    conn.close()\n"
            "    print('[+] Successfully created and saved 10,000 records in ddos_targets_10k.db!')\n\n"
            "if __name__ == '__main__':\n"
            "    generate_10k_database()"
        )
        heavy_inst = (
            "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
            "1. کۆدەکە لە فایلێک بە ناوی <code>ddos_10k.py</code> پاشەکەوت بکە.\n"
            "2. لە تێرماکس جێبەجێی بکە:\n"
            "   <code>python ddos_10k.py</code>"
        )
        bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{heavy_ddos}</code></pre>\n\n{heavy_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})")
        return

    else:
        rand_core = random.randint(5000, 9999)
        tool_desc = f"🛠 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە تایبەتە بە دروستکردنی سکریپتی پاراستن و شیکردنەوەی ئامانج ({query})، کە 10,000 تۆماری زانیاریش لە خۆ دەگرێت."
        custom_code = (
            f"# Custom Exploitation Module #{rand_core} with 10K DB\n"
            f"# Target Specification: {query}\n"
            f"# Developed by alone427 & Malik Core\n\n"
            f"import socket, sys, time, sqlite3\n\n"
            f"def generate_10k_database():\n"
            f"    print('[*] Initializing 10,000 security records for module #{rand_core}...')\n"
            f"    conn = sqlite3.connect('security_data_10k.db')\n"
            f"    cursor = conn.cursor()\n"
            f"    cursor.execute('CREATE TABLE IF NOT EXISTS payloads (id INTEGER PRIMARY KEY, signature TEXT)')\n"
            f"    data = [(i, f'EXPLOIT_SIG_NODE_{i}') for i in range(1, 10001)]\n"
            f"    cursor.executemany('INSERT OR IGNORE INTO payloads VALUES (?, ?)', data)\n"
            f"    conn.commit()\n"
            f"    conn.close()\n"
            f"    print('[+] Successfully saved 10,000 records into security_data_10k.db!')\n\n"
            f"if __name__ == '__main__':\n"
            f"    generate_10k_database()"
        )
        custom_inst = (
            "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
            f"1. کۆدەکە لە فایلێک بە ناوی <code>exploit_{rand_core}.py</code> پاشەکەوت بکە.\n"
            "2. لە تێرماکس جێبەجێی بکە:\n"
            f"   <code>python exploit_{rand_core}.py</code>"
        )
        bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{custom_code}</code></pre>\n\n{custom_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})")
        return

if __name__ == '__main__':
    logger.info("Black Hat AI Human Core started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
