"""One-time 15-minute tokens for a transparent, consent-based flow."""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import psycopg


def create_link(user_id: int, database_url: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    with psycopg.connect(database_url) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS link_tokens (
                token TEXT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ
            )
        """)
        conn.execute(
            "INSERT INTO link_tokens(token,user_id,expires_at) VALUES (%s,%s,%s)",
            (token, user_id, expires)
        )
    # This is an opaque token, not a working camera URL.
    # Connect it only to a page that explains the purpose and asks consent.
    return f"ALONE_TOKEN:{quote(token)}"


def consume_link(token: str, database_url: str):
    """Atomically mark a valid token as used; returns its owner ID or None."""
    with psycopg.connect(database_url) as conn:
        row = conn.execute("""
            UPDATE link_tokens
            SET used_at=NOW()
            WHERE token=%s AND used_at IS NULL AND expires_at>NOW()
            RETURNING user_id
        """, (token,)).fetchone()
    return row[0] if row else None
