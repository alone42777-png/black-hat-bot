"""
ALONE Telegram Bot
GitHub Actions scheduled-run edition.
Uses PostgreSQL because GitHub-hosted runners are temporary.
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta, timezone

import requests
import psycopg
from psycopg.rows import dict_row
from links import create_link, consume_link

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]
OWNER_IDS = {
    int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",")
    if x.strip().isdigit()
}
CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()  # e.g. @YourChannel; optional
CHANNEL_URL = os.getenv("CHANNEL_URL", "").strip()
FOOTER = (
    "\n\n🎁 هەر کەسێک کێشەیەک لە بۆت بدۆزێتەوە، خەڵات دەکرێت."
    "\n👑 Owners: @malikdlashad3 @ALONE427"
)
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("ALONE")


def db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=15)


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                credits INTEGER NOT NULL DEFAULT 0,
                banned_until TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                admin_id BIGINT,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id BIGSERIAL PRIMARY KEY,
                admin_id BIGINT NOT NULL,
                message TEXT NOT NULL,
                sent_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)


def api(method, payload=None):
    try:
        response = requests.post(
            f"{API}/{method}", json=payload or {}, timeout=25
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            log.warning("Telegram API %s failed: %s", method, data)
        return data
    except requests.RequestException:
        log.exception("Telegram API request failed: %s", method)
        return {"ok": False, "description": "network error"}


def send(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text[:4000] + FOOTER}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api("sendMessage", payload)


def answer_callback(callback_id, text=""):
    api("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


def is_owner(user_id):
    return user_id in OWNER_IDS


def register_user(user):
    with db() as conn:
        conn.execute("""
            INSERT INTO users(user_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT(user_id) DO UPDATE SET
                username=EXCLUDED.username,
                first_name=EXCLUDED.first_name,
                last_seen=NOW()
        """, (user["id"], user.get("username"), user.get("first_name")))


def get_user(user_id):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id=%s", (user_id,)
        ).fetchone()


def blocked(user_id):
    row = get_user(user_id)
    if not row:
        return False
    until = row["banned_until"]
    return bool(until and until > datetime.now(timezone.utc))


def member_ok(user_id):
    if not CHANNEL:
        return True
    result = api("getChatMember", {"chat_id": CHANNEL, "user_id": user_id})
    if not result.get("ok"):
        return False
    status = result["result"].get("status")
    return status in ("creator", "administrator", "member")


def start_keyboard():
    rows = [
        [{"text": "💳 باڵانسی من", "callback_data": "balance"},
         {"text": "🔗 دروستکردنی لینک", "callback_data": "newlink"}],
        [{"text": "ℹ️ یارمەتی", "callback_data": "help"}]
    ]
    return {"inline_keyboard": rows}


def panel_keyboard():
    return {"inline_keyboard": [
        [{"text": "📊 ئامار", "callback_data": "stats"},
         {"text": "👥 بەکارهێنەران", "callback_data": "users"}],
        [{"text": "🧾 دوا مامەڵەکان", "callback_data": "transactions"},
         {"text": "🔄 نوێکردنەوە", "callback_data": "stats"}],
    ]}


def help_text():
    return (
        "🤖 ALONE — ڕێنمایی\n\n"
        "/start — دەستپێکردن\n"
        "/balance — باڵانس\n"
        "/help — یارمەتی\n\n"
        "فەرمانەکانی خاوەن:\n"
        "/panel\n"
        "/addcredit USER_ID AMOUNT\n"
        "/removecredit USER_ID AMOUNT\n"
        "/ban USER_ID 30m|2h|3d|2w|1mo|1y|forever\n"
        "/unban USER_ID\n"
        "/dm USER_ID MESSAGE\n"
        "/broadcast MESSAGE\n"
        "/stats\n"
        "/history USER_ID"
    )


def credit_change(admin_id, user_id, amount, reason):
    if amount <= 0:
        raise ValueError("Amount must be positive")
    with db() as conn:
        row = conn.execute(
            "SELECT credits FROM users WHERE user_id=%s FOR UPDATE",
            (user_id,)
        ).fetchone()
        if not row:
            raise ValueError("User not found")
        new_value = row["credits"] + amount
        if new_value < 0:
            raise ValueError("Not enough credits")
        conn.execute(
            "UPDATE users SET credits=%s WHERE user_id=%s",
            (new_value, user_id)
        )
        conn.execute("""
            INSERT INTO transactions(user_id, admin_id, amount, reason)
            VALUES (%s, %s, %s, %s)
        """, (user_id, admin_id, amount, reason))
    return new_value


def parse_duration(value):
    value = value.lower().strip()
    if value == "forever":
        return datetime(9999, 12, 31, tzinfo=timezone.utc)
    units = {
        "m": 60, "h": 3600, "d": 86400,
        "w": 604800, "mo": 2592000, "y": 31536000
    }
    for unit in ("mo", "m", "h", "d", "w", "y"):
        if value.endswith(unit):
            number = int(value[:-len(unit)])
            if number <= 0:
                break
            return datetime.now(timezone.utc) + timedelta(seconds=number * units[unit])
    raise ValueError("Use 30m, 2h, 3d, 2w, 1mo, 1y, or forever")


def stats_text():
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        active = conn.execute("""
            SELECT COUNT(*) AS n FROM users
            WHERE last_seen > NOW() - INTERVAL '7 days'
        """).fetchone()["n"]
        credits = conn.execute(
            "SELECT COALESCE(SUM(credits),0) AS n FROM users"
        ).fetchone()["n"]
        banned = conn.execute("""
            SELECT COUNT(*) AS n FROM users
            WHERE banned_until > NOW()
        """).fetchone()["n"]
    return (
        "📊 ALONE — ئامار\n\n"
        f"👥 کۆی بەکارهێنەران: {total}\n"
        f"🟢 چالاک لە ٧ ڕۆژی ڕابردوو: {active}\n"
        f"🚫 باندکراو: {banned}\n"
        f"💳 کۆی کرێدیت: {credits}"
    )


def broadcast(admin_id, message):
    with db() as conn:
        ids = conn.execute("SELECT user_id FROM users").fetchall()
        cur = conn.execute("""
            INSERT INTO broadcasts(admin_id, message)
            VALUES (%s, %s) RETURNING id
        """, (admin_id, message))
        broadcast_id = cur.fetchone()["id"]
    sent_count = failed_count = 0
    for item in ids:
        result = api("sendMessage", {
            "chat_id": item["user_id"], "text": message[:4000] + FOOTER
        })
        if result.get("ok"):
            sent_count += 1
        else:
            failed_count += 1
        time.sleep(0.05)  # conservative pacing
    with db() as conn:
        conn.execute("""
            UPDATE broadcasts SET sent_count=%s, failed_count=%s WHERE id=%s
        """, (sent_count, failed_count, broadcast_id))
    return sent_count, failed_count


def command(update):
    message = update.get("message") or {}
    user = message.get("from", {})
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if not user or chat_id is None:
        return
    register_user(user)
    uid = user["id"]

    if blocked(uid):
        send(chat_id, "🚫 ئەم هەژمارە باندکراوە. بۆ زانیاری زیاتر پەیوەندی بە خاوەنەکان بکە.")
        return

    if text.startswith("/start"):
        if not member_ok(uid):
            msg = "سەرەتا پەیوەندی بە کەناڵەکەوە بکە، پاشان /start بنێرە."
            if CHANNEL_URL:
                send(chat_id, msg, {"inline_keyboard": [[
                    {"text": "📢 چوونە ناو کەناڵ", "url": CHANNEL_URL}
                ]]})
            else:
                send(chat_id, msg)
            return
        send(chat_id, "بەخێربێیت بۆ ALONE ⚡", start_keyboard())
        return

    if text == "/help":
        send(chat_id, help_text())
        return
    if text == "/balance":
        row = get_user(uid)
        send(chat_id, f"💳 باڵانسی تۆ: {row['credits']} Credit")
        return

    if not is_owner(uid):
        send(chat_id, "ئەم فەرمانە تەنها بۆ خاوەنەکانە.")
        return

    parts = text.split(maxsplit=2)
    cmd = parts[0].split("@")[0].lower()

    try:
        if cmd == "/panel":
            send(chat_id, "👑 کۆنترۆڵی ALONE", panel_keyboard())
        elif cmd == "/stats":
            send(chat_id, stats_text())
        elif cmd in ("/addcredit", "/removecredit") and len(parts) >= 3:
            target, amount = int(parts[1]), int(parts[2])
            if cmd == "/removecredit":
                amount = -amount
            value = credit_change(uid, target, amount, cmd)
            send(chat_id, f"✅ نوێکرایەوە. باڵانسی {target}: {value}")
            send(target, f"💳 گۆڕانکاری لە کرێدیتەکەت کرا. باڵانسی ئێستا: {value}")
        elif cmd == "/ban" and len(parts) >= 3:
            target = int(parts[1])
            until = parse_duration(parts[2])
            with db() as conn:
                conn.execute(
                    "UPDATE users SET banned_until=%s WHERE user_id=%s",
                    (until, target)
                )
            send(chat_id, f"🚫 بەکارهێنەری {target} باندکرا.")
            send(target, "🚫 هەژمارەکەت لەلایەن خاوەنەکانی ALONE باندکراوە. بۆ داوای پێداچوونەوە پەیوەندی بە @malikdlashad3 یان @ALONE427 بکە.")
        elif cmd == "/unban" and len(parts) >= 2:
            target = int(parts[1])
            with db() as conn:
                conn.execute(
                    "UPDATE users SET banned_until=NULL WHERE user_id=%s",
                    (target,)
                )
            send(chat_id, f"✅ باندی {target} لابرا.")
            send(target, "✅ باندەکەت لابرا.")
        elif cmd == "/dm" and len(parts) >= 3:
            target = int(parts[1])
            api("sendMessage", {"chat_id": target, "text": parts[2][:4000] + FOOTER})
            send(chat_id, "✅ نامەکە نێردرا.")
        elif cmd == "/broadcast" and len(parts) >= 2:
            sent, failed = broadcast(uid, text.split(maxsplit=1)[1])
            send(chat_id, f"📣 تەواو بوو.\n✅ نێردرا: {sent}\n❌ سەرکەوتوو نەبوو: {failed}")
        elif cmd == "/history" and len(parts) >= 2:
            target = int(parts[1])
            with db() as conn:
                rows = conn.execute("""
                    SELECT amount, reason, created_at FROM transactions
                    WHERE user_id=%s ORDER BY id DESC LIMIT 10
                """, (target,)).fetchall()
            if not rows:
                send(chat_id, "هیچ مامەڵەیەک نەدۆزرایەوە.")
            else:
                lines = [f"{r['created_at']:%Y-%m-%d %H:%M} | {r['amount']:+} | {r['reason']}" for r in rows]
                send(chat_id, "🧾 دوا مامەڵەکان:\n" + "\n".join(lines))
        else:
            send(chat_id, help_text())
    except (ValueError, TypeError, KeyError) as exc:
        send(chat_id, f"⚠️ هەڵە: {exc}")
    except Exception:
        log.exception("Command processing error")
        send(chat_id, "⚠️ هەڵەیەک ڕوویدا. تکایە دواتر هەوڵ بدەرەوە.")


def callback(update):
    cb = update.get("callback_query", {})
    user = cb.get("from", {})
    uid = user.get("id")
    chat_id = (cb.get("message") or {}).get("chat", {}).get("id")
    data = cb.get("data", "")
    if uid:
        register_user(user)
    if uid and blocked(uid):
        answer_callback(cb["id"], "هەژمارەکەت باندکراوە.")
        return
    if data == "balance":
        row = get_user(uid)
        send(chat_id, f"💳 باڵانسی تۆ: {row['credits']} Credit")
    elif data == "help":
        send(chat_id, help_text())
    elif data == "stats" and is_owner(uid):
        send(chat_id, stats_text())
    elif data == "users" and is_owner(uid):
        with db() as conn:
            rows = conn.execute("""
                SELECT user_id, username, credits FROM users
                ORDER BY created_at DESC LIMIT 15
            """).fetchall()
        lines = [f"{r['user_id']} | @{r['username'] or '-'} | {r['credits']} cr" for r in rows]
        send(chat_id, "👥 دوا بەکارهێنەران:\n" + ("\n".join(lines) or "بەتاڵە"))
    elif data == "transactions" and is_owner(uid):
        with db() as conn:
            rows = conn.execute("""
                SELECT user_id, amount, reason FROM transactions
                ORDER BY id DESC LIMIT 10
            """).fetchall()
        lines = [f"{r['user_id']} | {r['amount']:+} | {r['reason']}" for r in rows]
        send(chat_id, "🧾 دوا مامەڵەکان:\n" + ("\n".join(lines) or "بەتاڵە"))
    elif data == "newlink":
        row = get_user(uid)
        if not row or row["credits"] < 1:
            send(chat_id, "❌ کرێدیتی پێویستت نییە.")
        else:
            token = create_link(uid, DATABASE_URL)
            credit_change(0, uid, -1, "link creation")
            send(chat_id, f"🔗 لینکی تایبەتت ئامادەیە:\n{token}\n\n⏳ ماوە: ١٥ خولەک\n⚠️ تەنها بۆ بەکارهێنانی یەکجارە و خزمەتگوزارییەکی ڕوون و بە ڕەزامەندیی بەکارهێنەرە.")
    answer_callback(cb["id"])


def get_offset():
    with db() as conn:
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key='update_offset'"
        ).fetchone()
        return int(row["value"]) if row else 0


def save_offset(offset):
    with db() as conn:
        conn.execute("""
            INSERT INTO bot_state(key, value) VALUES ('update_offset', %s)
            ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value
        """, (str(offset),))


def main():
    init_db()
    offset = get_offset()
    # One short polling batch per GitHub Actions run.
    result = api("getUpdates", {
        "offset": offset,
        "timeout": 0,
        "allowed_updates": ["message", "callback_query"]
    })
    if not result.get("ok"):
        raise RuntimeError("getUpdates failed; check token and webhook status.")
    updates = result.get("result", [])
    for item in updates:
        try:
            if "message" in item:
                command(item)
            elif "callback_query" in item:
                callback(item)
        except Exception:
            log.exception("Update processing failed: %s", item.get("update_id"))
        save_offset(item["update_id"] + 1)
    log.info("ALONE processed %d updates", len(updates))


if __name__ == "__main__":
    main()
