import json
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def get_connection():
    """PostgreSQL 또는 SQLite 연결을 반환합니다."""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    if DATABASE_URL:
        # Railway PostgreSQL 환경
        import psycopg2
        from psycopg2.extras import DictCursor
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        # 로컬 SQLite 환경
        import sqlite3
        from pathlib import Path
        DB_PATH = Path(__file__).parent / "subscribers.db"
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_db() -> None:
    """데이터베이스 테이블을 초기화합니다."""
    conn = get_connection()
    try:
        if hasattr(conn, 'cursor') and os.environ.get("DATABASE_URL"):
            # PostgreSQL
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS subscribers (
                        id SERIAL PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        token TEXT UNIQUE NOT NULL,
                        active INTEGER NOT NULL DEFAULT 1,
                        subscribed_at TEXT NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS newsletters (
                        news_date TEXT PRIMARY KEY,
                        summaries_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
            conn.commit()
        else:
            # SQLite
            with conn:
                conn.executescript("""
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
                """)
    finally:
        conn.close()


def add_subscriber(email: str) -> tuple[str, bool]:
    """구독자를 등록하고 (token, 신규 여부)를 반환합니다."""
    now = datetime.now(KST).isoformat()
    conn = get_connection()
    try:
        if hasattr(conn, 'cursor') and os.environ.get("DATABASE_URL"):
            # PostgreSQL
            from psycopg2.extras import DictCursor
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT token FROM subscribers WHERE email = %s", (email,))
                existing = cur.fetchone()
                
                if existing:
                    cur.execute("UPDATE subscribers SET active = 1 WHERE email = %s", (email,))
                    conn.commit()
                    return existing["token"], False
                
                token = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO subscribers (email, token, active, subscribed_at) VALUES (%s, %s, 1, %s)",
                    (email, token, now)
                )
                conn.commit()
                return token, True
        else:
            # SQLite
            with conn:
                existing = conn.execute("SELECT token FROM subscribers WHERE email = ?", (email,)).fetchone()
                
                if existing:
                    conn.execute("UPDATE subscribers SET active = 1 WHERE email = ?", (email,))
                    return existing["token"], False
                
                token = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO subscribers (email, token, active, subscribed_at) VALUES (?, ?, 1, ?)",
                    (email, token, now)
                )
                return token, True
    finally:
        conn.close()


def unsubscribe(token: str) -> str | None:
    """구독을 취소하고 이메일 주소를 반환합니다."""
    conn = get_connection()
    try:
        if hasattr(conn, 'cursor') and os.environ.get("DATABASE_URL"):
            # PostgreSQL
            from psycopg2.extras import DictCursor
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT email FROM subscribers WHERE token = %s AND active = 1", (token,))
                row = cur.fetchone()
                
                if not row:
                    return None
                
                cur.execute("UPDATE subscribers SET active = 0 WHERE token = %s", (token,))
                conn.commit()
                return row["email"]
        else:
            # SQLite
            with conn:
                row = conn.execute("SELECT email FROM subscribers WHERE token = ? AND active = 1", (token,)).fetchone()
                
                if not row:
                    return None
                
                conn.execute("UPDATE subscribers SET active = 0 WHERE token = ?", (token,))
                return row["email"]
    finally:
        conn.close()


def get_active_subscribers() -> list[dict]:
    """활성화된 구독자 목록을 반환합니다."""
    conn = get_connection()
    try:
        if hasattr(conn, 'cursor') and os.environ.get("DATABASE_URL"):
            # PostgreSQL
            from psycopg2.extras import DictCursor
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT email, token FROM subscribers WHERE active = 1 ORDER BY id")
                rows = cur.fetchall()
                return [{"email": row["email"], "token": row["token"]} for row in rows]
        else:
            # SQLite
            with conn:
                rows = conn.execute("SELECT email, token FROM subscribers WHERE active = 1 ORDER BY id").fetchall()
                return [{"email": row["email"], "token": row["token"]} for row in rows]
    finally:
        conn.close()


def save_newsletter(news_date: str, summaries: list[dict]) -> None:
    """뉴스레터를 저장합니다."""
    now = datetime.now(KST).isoformat()
    payload = json.dumps(summaries, ensure_ascii=False)
    conn = get_connection()
    try:
        if hasattr(conn, 'cursor') and os.environ.get("DATABASE_URL"):
            # PostgreSQL
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO newsletters (news_date, summaries_json, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(news_date) DO UPDATE SET
                        summaries_json = EXCLUDED.summaries_json,
                        created_at = EXCLUDED.created_at
                """, (news_date, payload, now))
            conn.commit()
        else:
            # SQLite
            with conn:
                conn.execute("""
                    INSERT INTO newsletters (news_date, summaries_json, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(news_date) DO UPDATE SET
                        summaries_json = excluded.summaries_json,
                        created_at = excluded.created_at
                """, (news_date, payload, now))
    finally:
        conn.close()


def get_newsletter(news_date: str) -> list[dict] | None:
    """뉴스레터를 가져옵니다."""
    conn = get_connection()
    try:
        if hasattr(conn, 'cursor') and os.environ.get("DATABASE_URL"):
            # PostgreSQL
            from psycopg2.extras import DictCursor
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT summaries_json FROM newsletters WHERE news_date = %s", (news_date,))
                row = cur.fetchone()
                
                if not row:
                    return None
                
                return json.loads(row["summaries_json"])
        else:
            # SQLite
            with conn:
                row = conn.execute("SELECT summaries_json FROM newsletters WHERE news_date = ?", (news_date,)).fetchone()
                
                if not row:
                    return None
                
                return json.loads(row["summaries_json"])
    finally:
        conn.close()

