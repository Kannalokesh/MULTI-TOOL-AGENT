"""
auth.py — Google OAuth + SQLite auth table + session management
"""
from __future__ import annotations

import sqlite3
import secrets
import time
from datetime import datetime, timezone
from typing import Optional


# ─── DB setup ────────────────────────────────────────────────────────────────
AUTH_DB = "auth.db"

def get_auth_conn():
    conn = sqlite3.connect(AUTH_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_db():
    conn = get_auth_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            google_id   TEXT PRIMARY KEY,
            email       TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            picture     TEXT,
            created_at  TEXT NOT NULL,
            last_login  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_token TEXT PRIMARY KEY,
            google_id     TEXT NOT NULL REFERENCES users(google_id) ON DELETE CASCADE,
            created_at    TEXT NOT NULL,
            expires_at    TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_google_id ON sessions(google_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires   ON sessions(expires_at);
    """)
    conn.commit()
    conn.close()

init_auth_db()   # ← runs automatically when auth.py is imported


# ─── User upsert ─────────────────────────────────────────────────────────────
def upsert_user(google_id: str, email: str, name: str, picture: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_auth_conn()
    conn.execute("""
        INSERT INTO users (google_id, email, name, picture, created_at, last_login)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(google_id) DO UPDATE SET
            email      = excluded.email,
            name       = excluded.name,
            picture    = excluded.picture,
            last_login = excluded.last_login
    """, (google_id, email, name, picture, now, now))
    conn.commit()
    row = conn.execute(
        "SELECT * FROM users WHERE google_id = ?", (google_id,)
    ).fetchone()
    conn.close()
    return dict(row)


# ─── Session management ───────────────────────────────────────────────────────
SESSION_TTL_SECONDS = 60 * 60 * 8   # 8 hours

def create_session(google_id: str) -> str:
    token   = secrets.token_urlsafe(48)
    now     = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(
        now.timestamp() + SESSION_TTL_SECONDS, tz=timezone.utc
    )
    conn = get_auth_conn()
    conn.execute("""
        INSERT INTO sessions (session_token, google_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
    """, (token, google_id, now.isoformat(), expires.isoformat()))
    conn.commit()
    conn.close()
    return token


def validate_session(token: str) -> Optional[dict]:
    """Return user dict if session is valid and not expired, else None."""
    if not token:
        return None
    now = datetime.now(timezone.utc).isoformat()
    conn = get_auth_conn()
    row = conn.execute("""
        SELECT u.*
        FROM sessions s
        JOIN users u ON s.google_id = u.google_id
        WHERE s.session_token = ?
          AND s.expires_at > ?
    """, (token, now)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_session(token: str):
    """Called on sign out — immediately invalidates the session."""
    conn = get_auth_conn()
    conn.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
    conn.commit()
    conn.close()


def purge_expired_sessions():
    """Cleans up expired rows — called once on each app load."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_auth_conn()
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    conn.commit()
    conn.close()


# ─── Rate limiting (in-memory, per user per minute) ──────────────────────────
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_MAX    = 20
RATE_LIMIT_WINDOW = 60

def check_rate_limit(google_id: str) -> tuple[bool, int, int]:
    now          = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps   = _rate_limit_store.get(google_id, [])
    timestamps   = [t for t in timestamps if t > window_start]
    if len(timestamps) >= RATE_LIMIT_MAX:
        _rate_limit_store[google_id] = timestamps
        return False, len(timestamps), 0
    timestamps.append(now)
    _rate_limit_store[google_id] = timestamps
    used      = len(timestamps)
    remaining = RATE_LIMIT_MAX - used
    return True, used, remaining