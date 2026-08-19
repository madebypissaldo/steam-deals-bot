"""SQLite persistence for Best Deals subscriptions and scan history."""

import os
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "steam_deals_bot.sqlite3"


def _db_path() -> Path:
    return Path(os.getenv("BEST_DEALS_DB_PATH", DEFAULT_DB_PATH))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    with _connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS telegram_subscribers (
                telegram_user_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS notified_deals (
                app_id INTEGER NOT NULL,
                final_cents INTEGER NOT NULL,
                discount_percent INTEGER NOT NULL,
                notified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (app_id, final_cents, discount_percent)
            );
            CREATE TABLE IF NOT EXISTS scheduler_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL
            );
        """)


def set_subscription(user_id: int | str, chat_id: int | str, enabled: bool) -> None:
    with _connect() as connection:
        connection.execute("""
            INSERT INTO telegram_subscribers (telegram_user_id, chat_id, enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                chat_id = excluded.chat_id,
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
        """, (str(user_id), str(chat_id), int(enabled)))


def is_subscribed(user_id: int | str) -> bool:
    with _connect() as connection:
        row = connection.execute("SELECT enabled FROM telegram_subscribers WHERE telegram_user_id = ?", (str(user_id),)).fetchone()
    return bool(row and row["enabled"])


def active_subscribers() -> list[sqlite3.Row]:
    with _connect() as connection:
        return connection.execute("SELECT telegram_user_id, chat_id FROM telegram_subscribers WHERE enabled = 1").fetchall()


def was_notified(deal: dict) -> bool:
    with _connect() as connection:
        row = connection.execute("""SELECT 1 FROM notified_deals
            WHERE app_id = ? AND final_cents = ? AND discount_percent = ?""",
            (deal["app_id"], deal["final_cents"], deal["discount_percent"])).fetchone()
    return row is not None


def mark_notified(deal: dict) -> None:
    with _connect() as connection:
        connection.execute("""INSERT OR IGNORE INTO notified_deals
            (app_id, final_cents, discount_percent) VALUES (?, ?, ?)""",
            (deal["app_id"], deal["final_cents"], deal["discount_percent"]))


def last_scan_date() -> str | None:
    with _connect() as connection:
        row = connection.execute("SELECT state_value FROM scheduler_state WHERE state_key = 'last_best_deals_scan'").fetchone()
    return row["state_value"] if row else None


def mark_scan_complete(scan_date: str) -> None:
    with _connect() as connection:
        connection.execute("""INSERT INTO scheduler_state (state_key, state_value) VALUES ('last_best_deals_scan', ?)
            ON CONFLICT(state_key) DO UPDATE SET state_value = excluded.state_value""", (scan_date,))
