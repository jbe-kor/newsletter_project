import sqlite3

conn = sqlite3.connect('subscribers.db')
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS subscribers")
cursor.execute("DROP TABLE IF EXISTS cached_newsletters")

cursor.execute("""
CREATE TABLE subscribers (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    unsubscribe_token TEXT UNIQUE NOT NULL
)
""")
cursor.execute("""
CREATE TABLE cached_newsletters (
    date_str TEXT PRIMARY KEY,
    summaries_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()
print("DB 스키마 수정 완료")
