import sqlite3
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

DATABASE_PATH = "app/database.db"


@contextmanager
def get_db():
    """데이터베이스 연결 컨텍스트 매니저"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """데이터베이스 테이블 생성 및 기본 데이터 삽입"""
    with get_db() as conn:
        cursor = conn.cursor()

        # categories 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at DATETIME NOT NULL
            )
        """)

        # channels 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                channel_input TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                title TEXT,
                subscriber_count INTEGER,
                country TEXT,
                language_hint TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                UNIQUE(category_id, channel_id)
            )
        """)

        # videos 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                video_id TEXT NOT NULL UNIQUE,
                title TEXT,
                published_at DATETIME,
                view_count INTEGER,
                thumbnail_url TEXT,
                duration_seconds INTEGER,
                is_short INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)

        # 인덱스 생성
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_channel_id
            ON videos(channel_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_published_at
            ON videos(published_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_view_count
            ON videos(view_count DESC)
        """)

        # downloads 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                status TEXT NOT NULL,
                file_path TEXT,
                error_message TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)

        # 기본 카테고리 삽입
        cursor.execute("""
            INSERT OR IGNORE INTO categories (name, created_at)
            VALUES (?, ?)
        """, ("기본", datetime.now().isoformat()))

        conn.commit()


def reset_db():
    """데이터베이스 초기화 (테스트용)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS downloads")
        cursor.execute("DROP TABLE IF EXISTS videos")
        cursor.execute("DROP TABLE IF EXISTS channels")
        cursor.execute("DROP TABLE IF EXISTS categories")
        conn.commit()
    init_db()
