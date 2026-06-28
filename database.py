import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
DB_PATH = Path(__file__).parent / "subscribers.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                token TEXT UNIQUE NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                subscribed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS newsletters (
                news_date TEXT PRIMARY KEY,
                summaries_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def add_subscriber(email: str) -> tuple[str, bool]:
    """구독자를 등록하고 (token, 신규 여부)를 반환합니다."""
    now = datetime.now(KST).isoformat()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT token FROM subscribers WHERE email = ?",
            (email,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE subscribers SET active = 1 WHERE email = ?",
                (email,),
            )
            return existing["token"], False

        token = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO subscribers (email, token, active, subscribed_at) VALUES (?, ?, 1, ?)",
            (email, token, now),
        )
        return token, True


def unsubscribe(token: str) -> str | None:
    """구독을 취소하고 이메일 주소를 반환합니다."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT email FROM subscribers WHERE token = ? AND active = 1",
            (token,),
        ).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE subscribers SET active = 0 WHERE token = ?",
            (token,),
        )
        return row["email"]


def get_active_subscribers() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT email, token FROM subscribers WHERE active = 1 ORDER BY id"
        ).fetchall()
        return [{"email": row["email"], "token": row["token"]} for row in rows]


def save_newsletter(news_date: str, summaries: list[dict]) -> None:
    now = datetime.now(KST).isoformat()
    payload = json.dumps(summaries, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO newsletters (news_date, summaries_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(news_date) DO UPDATE SET
                summaries_json = excluded.summaries_json,
                created_at = excluded.created_at
            """,
            (news_date, payload, now),
        )


def get_newsletter(news_date: str) -> list[dict] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT summaries_json FROM newsletters WHERE news_date = ?",
            (news_date,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["summaries_json"])

