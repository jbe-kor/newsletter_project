"""
Database 모듈
- 구독자 관리
- 뉴스레터 캐싱
"""
import datetime
import os
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any, Iterator, Optional

import psycopg2
from psycopg2.extras import DictCursor

# --- 데이터 클래스 ---
@dataclass
class Subscriber:
    id: str
    email: str
    created_at: datetime.datetime
    is_active: bool
    unsubscribe_token: str


@dataclass
class CachedNewsletter:
    date_str: str
    summaries_json: str
    created_at: datetime.datetime


# --- DB 설정 ---
def get_db_connection():
    """데이터베이스 연결을 반환합니다. DATABASE_URL이 있으면 PostgreSQL, 없으면 SQLite"""
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # PostgreSQL 연결
        conn = psycopg2.connect(database_url)
        return conn
    else:
        # SQLite 연결 (로컬 개발용)
        conn = sqlite3.connect("subscribers.db", detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """데이터베이스 테이블 초기화"""
    conn = get_db_connection()
    cursor = conn.cursor()

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # PostgreSQL용 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                unsubscribe_token TEXT UNIQUE NOT NULL
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cached_newsletters (
                date_str TEXT PRIMARY KEY,
                summaries_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
    else:
        # SQLite용 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                unsubscribe_token TEXT UNIQUE NOT NULL
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cached_newsletters (
                date_str TEXT PRIMARY KEY,
                summaries_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    conn.commit()
    conn.close()


# --- 구독자 관리 ---
def add_subscriber(email: str) -> Subscriber:
    """새 구독자를 추가합니다. (이미 존재하면 활성화만)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 먼저 존재하는지 확인
    cursor.execute("SELECT * FROM subscribers WHERE email = %s" if os.getenv("DATABASE_URL") else "SELECT * FROM subscribers WHERE email = ?", (email,))
    row = cursor.fetchone()

    unsubscribe_token = str(uuid.uuid4())
    subscriber_id = str(uuid.uuid4())

    if row:
        # 이미 존재하면 활성화 & 토큰 업데이트
        cursor.execute(
            "UPDATE subscribers SET is_active = %s, unsubscribe_token = %s WHERE email = %s" if os.getenv("DATABASE_URL") else "UPDATE subscribers SET is_active = ?, unsubscribe_token = ? WHERE email = ?",
            (True, unsubscribe_token, email)
        )
        subscriber_id = row[0]
    else:
        # 새로 추가
        cursor.execute(
            "INSERT INTO subscribers (id, email, unsubscribe_token) VALUES (%s, %s, %s)" if os.getenv("DATABASE_URL") else "INSERT INTO subscribers (id, email, unsubscribe_token) VALUES (?, ?, ?)",
            (subscriber_id, email, unsubscribe_token)
        )

    conn.commit()

    # 다시 조회
    cursor.execute("SELECT * FROM subscribers WHERE email = %s" if os.getenv("DATABASE_URL") else "SELECT * FROM subscribers WHERE email = ?", (email,))
    row = cursor.fetchone()

    conn.close()

    return _row_to_subscriber(row)


def get_subscriber_by_token(token: str) -> Optional[Subscriber]:
    """Unsubscribe 토큰으로 구독자를 찾습니다."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subscribers WHERE unsubscribe_token = %s" if os.getenv("DATABASE_URL") else "SELECT * FROM subscribers WHERE unsubscribe_token = ?", (token,))
    row = cursor.fetchone()
    conn.close()

    return _row_to_subscriber(row) if row else None


def unsubscribe(token: str) -> bool:
    """구독을 취소합니다."""
    subscriber = get_subscriber_by_token(token)
    if not subscriber:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subscribers SET is_active = %s WHERE unsubscribe_token = %s" if os.getenv("DATABASE_URL") else "UPDATE subscribers SET is_active = ? WHERE unsubscribe_token = ?",
        (False, token)
    )
    conn.commit()
    conn.close()
    return True


def get_active_subscribers() -> Iterator[Subscriber]:
    """활성 구독자 목록을 반환합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subscribers WHERE is_active = %s" if os.getenv("DATABASE_URL") else "SELECT * FROM subscribers WHERE is_active = 1", (True,))
    rows = cursor.fetchall()

    conn.close()

    for row in rows:
        yield _row_to_subscriber(row)


def _row_to_subscriber(row: Any) -> Subscriber:
    return Subscriber(
        id=row[0],
        email=row[1],
        created_at=row[2],
        is_active=bool(row[3]),
        unsubscribe_token=row[4],
    )


# --- 뉴스레터 캐싱 ---
def cache_newsletter(date_str: str, summaries_json: str) -> None:
    """뉴스레터를 캐싱합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        cursor.execute(
            """
            INSERT INTO cached_newsletters (date_str, summaries_json)
            VALUES (%s, %s)
            ON CONFLICT (date_str) DO UPDATE SET summaries_json = %s
        """,
            (date_str, summaries_json, summaries_json)
        )
    else:
        cursor.execute(
            """
            INSERT OR REPLACE INTO cached_newsletters (date_str, summaries_json)
            VALUES (?, ?)
        """,
            (date_str, summaries_json)
        )

    conn.commit()
    conn.close()


def get_cached_newsletter(date_str: str) -> Optional[CachedNewsletter]:
    """캐싱된 뉴스레터를 가져옵니다."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cached_newsletters WHERE date_str = %s" if os.getenv("DATABASE_URL") else "SELECT * FROM cached_newsletters WHERE date_str = ?", (date_str,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return CachedNewsletter(
        date_str=row[0],
        summaries_json=row[1],
        created_at=row[2],
    )