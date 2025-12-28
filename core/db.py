"""
Database operations for YouTube analytics app
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager
import json

from .models import (
    Channel, ChannelSnapshot, Video, VideoSnapshot,
    Watchlist, NicheRun, NicheCluster
)


DB_PATH = "db.sqlite"


@contextmanager
def get_db():
    """Context manager for database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """Initialize database schema"""
    with get_db() as conn:
        cursor = conn.cursor()

        # channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                youtube_channel_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                handle TEXT,
                thumbnail_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_fetched_at TIMESTAMP
            )
        """)

        # channel_snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subscriber_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                video_count INTEGER DEFAULT 0,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_snapshots_channel_id
            ON channel_snapshots(channel_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_snapshots_fetched_at
            ON channel_snapshots(fetched_at)
        """)

        # videos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                youtube_video_id TEXT UNIQUE NOT NULL,
                channel_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                published_at TIMESTAMP,
                duration_seconds INTEGER DEFAULT 0,
                tags_json TEXT DEFAULT '[]',
                thumbnail_url TEXT,
                last_fetched_at TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_channel_id
            ON videos(channel_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_published_at
            ON videos(published_at)
        """)

        # video_snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_snapshots_video_id
            ON video_snapshots(video_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_snapshots_fetched_at
            ON video_snapshots(fetched_at)
        """)

        # watchlists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # watchlist_channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_channels (
                watchlist_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                PRIMARY KEY (watchlist_id, channel_id),
                FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        """)

        # niche_runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS niche_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                params_json TEXT DEFAULT '{}'
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_niche_runs_keyword
            ON niche_runs(keyword)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_niche_runs_fetched_at
            ON niche_runs(fetched_at)
        """)

        # niche_clusters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS niche_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                niche_run_id INTEGER NOT NULL,
                cluster_index INTEGER NOT NULL,
                label TEXT,
                metrics_json TEXT DEFAULT '{}',
                sample_videos_json TEXT DEFAULT '[]',
                sample_channels_json TEXT DEFAULT '[]',
                FOREIGN KEY (niche_run_id) REFERENCES niche_runs(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_niche_clusters_run_id
            ON niche_clusters(niche_run_id)
        """)

        conn.commit()


# ========== Channel Operations ==========

def insert_channel(channel: Channel) -> int:
    """Insert or update channel, return channel ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO channels (youtube_channel_id, title, handle, thumbnail_url, last_fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(youtube_channel_id) DO UPDATE SET
                title = excluded.title,
                handle = excluded.handle,
                thumbnail_url = excluded.thumbnail_url,
                last_fetched_at = excluded.last_fetched_at
        """, (channel.youtube_channel_id, channel.title, channel.handle,
              channel.thumbnail_url, channel.last_fetched_at))

        cursor.execute("SELECT id FROM channels WHERE youtube_channel_id = ?",
                      (channel.youtube_channel_id,))
        return cursor.fetchone()[0]


def get_channel_by_id(channel_id: int) -> Optional[Channel]:
    """Get channel by internal ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
        if row:
            return Channel.from_db_row(row)
        return None


def get_channel_by_youtube_id(youtube_channel_id: str) -> Optional[Channel]:
    """Get channel by YouTube channel ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE youtube_channel_id = ?",
                      (youtube_channel_id,))
        row = cursor.fetchone()
        if row:
            return Channel.from_db_row(row)
        return None


def get_all_channels() -> List[Channel]:
    """Get all channels"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels ORDER BY created_at DESC")
        return [Channel.from_db_row(row) for row in cursor.fetchall()]


def delete_channel(channel_id: int):
    """Delete channel and all related data"""
    with get_db() as conn:
        cursor = conn.cursor()

        # First, manually delete related records to avoid foreign key issues
        # Delete video snapshots
        cursor.execute("""
            DELETE FROM video_snapshots
            WHERE video_id IN (SELECT id FROM videos WHERE channel_id = ?)
        """, (channel_id,))

        # Delete videos
        cursor.execute("DELETE FROM videos WHERE channel_id = ?", (channel_id,))

        # Delete channel snapshots
        cursor.execute("DELETE FROM channel_snapshots WHERE channel_id = ?", (channel_id,))

        # Delete watchlist associations
        cursor.execute("DELETE FROM watchlist_channels WHERE channel_id = ?", (channel_id,))

        # Finally, delete the channel
        cursor.execute("DELETE FROM channels WHERE id = ?", (channel_id,))

        return True


def should_fetch_channel(youtube_channel_id: str, hours: int = 12) -> bool:
    """Check if channel should be fetched based on last fetch time"""
    channel = get_channel_by_youtube_id(youtube_channel_id)
    if not channel or not channel.last_fetched_at:
        return True

    threshold = datetime.now() - timedelta(hours=hours)
    return channel.last_fetched_at < threshold


# ========== Channel Snapshot Operations ==========

def insert_channel_snapshot(snapshot: ChannelSnapshot) -> int:
    """Insert channel snapshot, return snapshot ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO channel_snapshots
            (channel_id, fetched_at, subscriber_count, view_count, video_count)
            VALUES (?, ?, ?, ?, ?)
        """, (snapshot.channel_id, snapshot.fetched_at, snapshot.subscriber_count,
              snapshot.view_count, snapshot.video_count))
        return cursor.lastrowid


def get_latest_channel_snapshot(channel_id: int) -> Optional[ChannelSnapshot]:
    """Get most recent snapshot for channel"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM channel_snapshots
            WHERE channel_id = ?
            ORDER BY fetched_at DESC LIMIT 1
        """, (channel_id,))
        row = cursor.fetchone()
        if row:
            return ChannelSnapshot.from_db_row(row)
        return None


def get_channel_snapshot_before(channel_id: int, days: int) -> Optional[ChannelSnapshot]:
    """Get snapshot from N days ago"""
    with get_db() as conn:
        cursor = conn.cursor()
        threshold = datetime.now() - timedelta(days=days)
        cursor.execute("""
            SELECT * FROM channel_snapshots
            WHERE channel_id = ? AND fetched_at <= ?
            ORDER BY fetched_at DESC LIMIT 1
        """, (channel_id, threshold))
        row = cursor.fetchone()
        if row:
            return ChannelSnapshot.from_db_row(row)
        return None


# ========== Video Operations ==========

def insert_video(video: Video) -> int:
    """Insert or update video, return video ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO videos
            (youtube_video_id, channel_id, title, description, published_at,
             duration_seconds, tags_json, thumbnail_url, last_fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(youtube_video_id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                duration_seconds = excluded.duration_seconds,
                tags_json = excluded.tags_json,
                thumbnail_url = excluded.thumbnail_url,
                last_fetched_at = excluded.last_fetched_at
        """, (video.youtube_video_id, video.channel_id, video.title,
              video.description, video.published_at, video.duration_seconds,
              video.tags_json, video.thumbnail_url, video.last_fetched_at))

        cursor.execute("SELECT id FROM videos WHERE youtube_video_id = ?",
                      (video.youtube_video_id,))
        return cursor.fetchone()[0]


def get_videos_by_channel(channel_id: int, limit: int = 50) -> List[Video]:
    """Get recent videos for channel"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM videos
            WHERE channel_id = ?
            ORDER BY published_at DESC
            LIMIT ?
        """, (channel_id, limit))
        return [Video.from_db_row(row) for row in cursor.fetchall()]


def get_video_by_id(video_id: int) -> Optional[Video]:
    """Get video by internal ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if row:
            return Video.from_db_row(row)
        return None


# ========== Video Snapshot Operations ==========

def insert_video_snapshot(snapshot: VideoSnapshot) -> int:
    """Insert video snapshot, return snapshot ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO video_snapshots
            (video_id, fetched_at, view_count, like_count, comment_count)
            VALUES (?, ?, ?, ?, ?)
        """, (snapshot.video_id, snapshot.fetched_at, snapshot.view_count,
              snapshot.like_count, snapshot.comment_count))
        return cursor.lastrowid


def get_latest_video_snapshot(video_id: int) -> Optional[VideoSnapshot]:
    """Get most recent snapshot for video"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM video_snapshots
            WHERE video_id = ?
            ORDER BY fetched_at DESC LIMIT 1
        """, (video_id,))
        row = cursor.fetchone()
        if row:
            return VideoSnapshot.from_db_row(row)
        return None


def get_video_snapshots(video_id: int) -> List[VideoSnapshot]:
    """Get all snapshots for video"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM video_snapshots
            WHERE video_id = ?
            ORDER BY fetched_at ASC
        """, (video_id,))
        return [VideoSnapshot.from_db_row(row) for row in cursor.fetchall()]


# ========== Watchlist Operations ==========

def create_watchlist(name: str) -> int:
    """Create watchlist, return watchlist ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO watchlists (name) VALUES (?)", (name,))
        return cursor.lastrowid


def get_all_watchlists() -> List[Watchlist]:
    """Get all watchlists"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlists ORDER BY name")
        return [Watchlist.from_db_row(row) for row in cursor.fetchall()]


def get_watchlist_by_id(watchlist_id: int) -> Optional[Watchlist]:
    """Get watchlist by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlists WHERE id = ?", (watchlist_id,))
        row = cursor.fetchone()
        if row:
            return Watchlist.from_db_row(row)
        return None


def delete_watchlist(watchlist_id: int):
    """Delete watchlist"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))


def add_channel_to_watchlist(watchlist_id: int, channel_id: int):
    """Add channel to watchlist"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO watchlist_channels (watchlist_id, channel_id)
            VALUES (?, ?)
        """, (watchlist_id, channel_id))


def remove_channel_from_watchlist(watchlist_id: int, channel_id: int):
    """Remove channel from watchlist"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM watchlist_channels
            WHERE watchlist_id = ? AND channel_id = ?
        """, (watchlist_id, channel_id))


def get_watchlist_channels(watchlist_id: int) -> List[Channel]:
    """Get all channels in watchlist"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.* FROM channels c
            JOIN watchlist_channels wc ON c.id = wc.channel_id
            WHERE wc.watchlist_id = ?
            ORDER BY c.title
        """, (watchlist_id,))
        return [Channel.from_db_row(row) for row in cursor.fetchall()]


# ========== Niche Operations ==========

def insert_niche_run(run: NicheRun) -> int:
    """Insert niche run, return run ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO niche_runs (keyword, fetched_at, params_json)
            VALUES (?, ?, ?)
        """, (run.keyword, run.fetched_at, run.params_json))
        return cursor.lastrowid


def get_recent_niche_run(keyword: str, params: Dict[str, Any],
                         hours: int = 24) -> Optional[NicheRun]:
    """Get recent niche run with same keyword and params"""
    with get_db() as conn:
        cursor = conn.cursor()
        threshold = datetime.now() - timedelta(hours=hours)
        params_json = json.dumps(params, sort_keys=True)

        cursor.execute("""
            SELECT * FROM niche_runs
            WHERE keyword = ? AND params_json = ? AND fetched_at >= ?
            ORDER BY fetched_at DESC LIMIT 1
        """, (keyword, params_json, threshold))

        row = cursor.fetchone()
        if row:
            return NicheRun.from_db_row(row)
        return None


def insert_niche_cluster(cluster: NicheCluster) -> int:
    """Insert niche cluster, return cluster ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO niche_clusters
            (niche_run_id, cluster_index, label, metrics_json,
             sample_videos_json, sample_channels_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cluster.niche_run_id, cluster.cluster_index, cluster.label,
              cluster.metrics_json, cluster.sample_videos_json,
              cluster.sample_channels_json))
        return cursor.lastrowid


def get_niche_clusters(niche_run_id: int) -> List[NicheCluster]:
    """Get all clusters for niche run"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM niche_clusters
            WHERE niche_run_id = ?
            ORDER BY cluster_index
        """, (niche_run_id,))
        return [NicheCluster.from_db_row(row) for row in cursor.fetchall()]
