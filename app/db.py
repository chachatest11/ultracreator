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
                description TEXT,
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

        # description 컬럼 추가 (기존 DB 마이그레이션)
        try:
            cursor.execute("ALTER TABLE channels ADD COLUMN description TEXT")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재함

        # videos 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                video_id TEXT NOT NULL UNIQUE,
                title TEXT,
                published_at DATETIME,
                view_count INTEGER,
                like_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                thumbnail_url TEXT,
                duration_seconds INTEGER,
                is_short INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)

        # like_count, comment_count 컬럼 추가 (기존 DB 마이그레이션)
        try:
            cursor.execute("ALTER TABLE videos ADD COLUMN like_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재함

        try:
            cursor.execute("ALTER TABLE videos ADD COLUMN comment_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # 컬럼이 이미 존재함

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

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_like_count
            ON videos(like_count DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_comment_count
            ON videos(comment_count DESC)
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

        # settings 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME NOT NULL
            )
        """)

        # api_keys 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL UNIQUE,
                name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                priority INTEGER NOT NULL DEFAULT 0,
                quota_exceeded INTEGER NOT NULL DEFAULT 0,
                last_used_at DATETIME,
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
