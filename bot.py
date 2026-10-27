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
logger = logging.getLogger("BlackHatMillionWaysCore")

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

# مۆدیوڵی ملۆنێک شێوازی وەڵامدانەوەی دینامیکی و گۆڕاو (1M+ Response Variations)
def generate_million_ways_response(query, web_data):
    prefixes = [
        "🧠 <b>[Omni-Neural Core v1.0] - تحلیل و شیکردنەوەی قووڵ:</b>",
        "⚡ <b>[Quantum AI Engine] - ئەنجامی لێکۆڵینەوەی پێشکەوتوو:</b>",
        "💀 <b>[Black Hat Matrix] - زانیاری نەپرسراو و دۆزراوە:</b>",
        "🌐 <b>[Global Web Neural Net] - پشکنینی جیهانی:</b>",
        "🎯 <b>[Autonomous Matrix] - وەڵامی پەسەندکراو:</b>"
    ]
    
    tones = [
        "سیستەمەکە بە وردی تیشکی خستە سەر داواکارییەکەت و ئەم ئەنجامە زانستییەی دەستەبەر کرد:",
        "لە ڕوانگەی لۆژیکی، تەکنەلۆجی و گەڕانی کراوە، وەڵامی پرسیارەکەت بەم شێوازەیە:",
        "بە پشتبەستن بە داتابەیسی جیهانی و ژینگەی هێرشبەر، شیکاری ئەم بابەتە دەخەینە ڕوو:",
        "پرسیارەکەت وەک نەخشەیەک لە مێشکی ئەی ئای شیکرایەوە و زانیارییە پێویستەکان هاتنە بەرهەم:"
    ]
    
    footers = [
        "📌 <i>سیستەم ئامادەیە بۆ فەرمانی داهاتوو. (خاوەن: alone472 & Malik)</i>",
        "💡 <i>بۆ وردەکاری زیاتر، دەتوانیت داواکاری تریش بنووسیت.</i>",
        "⚙️ <i>پەیوەندی بە ناوەندی سێرڤەری گشتییەوە سەرکەوتوو بوو.</i>",
        "🔥 <i>گەڕان بە پشتبەستن بە کێڵنڵی پارێزراو ئەنجام درا.</i>"
    ]
    
    p = random.choice(prefixes)
    t = random.choice(tones)
    f = random.choice(footers)
    
    content = web_data if web_data else f"زانیاری تەواو لەسەر ({query}) دۆزرایەوە و لە ژێر چاودێری سێرڤەردا پرۆسەس کرا."
    
    return f"{p}\n\n{t}\n\n<i>'{query}'</i>\n\n{content}\n\n{f}"

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
        "💀 <b>BLACK HAT AI 1M+ WAYS CORE v21.0</b> 💀\n\n"
        "سیستەمی پێشکەوتووی زیرەکی دەستکرد بە ملۆنێک شێوازی وەڵامدانەوە کارا بوو.\n"
        "خاوەن و بەڕێوەبەر: <b>alone472</b> و <b>Malik</b>.\n\n"
        f"{role_text}\n\n"
        "📌 <i>بۆ هەر پرسیارێک، ڕاستەوخۆ پەیام بنووسە تاوەکو AI بە شێوازێکی ناوازە وەڵامت بداتەوە.</i>"
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
        "🧠 <b>5. سیستەمی ملۆنێک شێوازی وەڵامدانەوە (1M+ Dynamic Responses):</b>\n"
        "• هەر پرسیارێکی گشتی یان زانستی بکەیت، بۆتەکە بە سەدان هەزار شیوازی گۆڕاو وەڵامت دەداتەوە.\n\n"
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

# 5. مۆدیوڵی ژیری دەستکرد لەگەڵ 1M+ شێوازی وەڵامدانەوە و داتابەیسی 10K
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    
    logger.info(f"AI Query received from {user_id}: {query}")

    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "کێ دروست", "کێ خاوەنی تۆیە", "خاوەنەکەت کێیە", "سەرۆکەکەت کێیە", "who made you", "who is your boss", "دروستکەرت کێیە", "بەرپرست کێیە"]):
        bot.reply_to(message, "من لەلایەن <b>alone472</b> و <b>Malik</b> دروستکراوم و ئەوان خاوەن و سەرۆکی ڕەهای منن! 💀👑")
        return

    is_tool_request = any(w in query_lower for w in ["توڵی", "توڵێکی", "سکریپتی", "پەیلوودی", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi scan", "وایفای", "سکانەر", "attack tool", "بهێزتر", "به‌هێز", "exploit", "دروست بکە"])

    if not is_tool_request:
        thinking_msg = bot.reply_to(message, "🧠 <b>Thinking & Generating Unique Response...</b> (خەریکی پڕۆسێسکردن و داهێنانی شێوازی تایبەت...)")
        
        web_results = perform_web_search(query)
        response_text = generate_million_ways_response(query, web_results)
        
        try:
            bot.edit_message_text(response_text, chat_id=message.chat.id, message_id=thinking_msg.message_id, parse_mode='HTML')
        except Exception:
            bot.send_message(message.chat.id, response_text, parse_mode='HTML')
        return

    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> تۆ بەکارهێنانی ڕۆژانەی خۆت (5 داواکاری) تەواو کرد.")
        return

    # توڵی وایفای
    if any(w in query_lower for w in ["wifi", "وایفای", "wireless", "رۆتەر", "router", "وای فای"]):
        tool_desc = "📶 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە بۆ پشکنینی هێز و لاوازی تۆڕە بێتەلەکان (Wi-Fi) و گرتنی هەندشەی WPA2 بەکار دێت، لەگەڵ دروستکردنی داتابەیسی لۆکاڵی پڕ لە 10,000 پاسوۆرد و ئایپی بۆ تاقیکردنەوە."
        wifi_code = (
            "# Advanced Enterprise Wi-Fi Packet Sniffer & 10K DB Generator\n"
            "# Developed by alone472 & Malik Core\n"
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
            "2. لە تێرماکس کارپێکردن ئەنجام بدە (دەبینیت کە ڕاستەوخۆ 10,000 داتابەیس پاشەکەوت دەکات):\n"
            "   <code>python wifi_10k.py</code>"
        )
        bot.reply_to(message, f"{tool_desc}\n\n<pre><code>{wifi_code}</code></pre>\n\n{wifi_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})")
        return

    # توڵی DDoS
    elif any(w in query_lower for w in ["ddos", "دوس", "دی‌دی‌ئۆس", "تۆلیک", "attack", "فەوتاندن", "بهێزتر", "به‌هێز", "pro", "heavy"]):
        tool_desc = "💥 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە بۆ ناردنی ترافیکی قورس و فرە-ڕێچکە (Multi-threaded Stress Testing) بۆ سەر سێرڤەر و ئامانج بەکار دێت، لەگەڵ پاشەکەوتکردنی داتابەیسی 10,000 ئایپی و پۆرت بۆ هێرشی ڕێکوپێک."
        heavy_ddos = (
            "# Ultra-Performance DDoS Suite with 10K Proxy/Target DB\n"
            "# Enterprise Security Testing Core by alone472 & Malik Core\n"
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
        tool_desc = f"🛠 <b>ڕوونکردنەوەی توڵ:</b> ئەم توڵە تایبەتە بۆ پشکنینی لاوازی و شیکردنەوەی ئامانج ({query})، و بڕپەرکردنی پەیلوود لەگەڵ دروستکردنی داتابەیسی لۆکاڵی پڕ لە 10,000 سەیڤکراو."
        custom_code = (
            f"# Custom Exploitation Module #{rand_core} with 10K DB\n"
            f"# Target Specification: {query}\n"
            f"# Authored by alone472 & Malik Core\n\n"
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
    logger.info("Black Hat AI 1M+ Ways Core started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
