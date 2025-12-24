"""
Data models for YouTube analytics app
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class Channel:
    """YouTube channel model"""
    id: Optional[int] = None
    youtube_channel_id: str = ""
    title: str = ""
    handle: str = ""
    thumbnail_url: str = ""
    created_at: Optional[datetime] = None
    last_fetched_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: tuple) -> 'Channel':
        """Create Channel from database row"""
        return cls(
            id=row[0],
            youtube_channel_id=row[1],
            title=row[2],
            handle=row[3],
            thumbnail_url=row[4],
            created_at=datetime.fromisoformat(row[5]) if row[5] else None,
            last_fetched_at=datetime.fromisoformat(row[6]) if row[6] else None
        )


@dataclass
class ChannelSnapshot:
    """Channel statistics snapshot"""
    id: Optional[int] = None
    channel_id: int = 0
    fetched_at: Optional[datetime] = None
    subscriber_count: int = 0
    view_count: int = 0
    video_count: int = 0

    @classmethod
    def from_db_row(cls, row: tuple) -> 'ChannelSnapshot':
        """Create ChannelSnapshot from database row"""
        return cls(
            id=row[0],
            channel_id=row[1],
            fetched_at=datetime.fromisoformat(row[2]) if row[2] else None,
            subscriber_count=row[3],
            view_count=row[4],
            video_count=row[5]
        )


@dataclass
class Video:
    """YouTube video model"""
    id: Optional[int] = None
    youtube_video_id: str = ""
    channel_id: int = 0
    title: str = ""
    description: str = ""
    published_at: Optional[datetime] = None
    duration_seconds: int = 0
    tags_json: str = "[]"
    thumbnail_url: str = ""
    last_fetched_at: Optional[datetime] = None

    @property
    def tags(self) -> List[str]:
        """Parse tags from JSON"""
        try:
            return json.loads(self.tags_json)
        except:
            return []

    @classmethod
    def from_db_row(cls, row: tuple) -> 'Video':
        """Create Video from database row"""
        return cls(
            id=row[0],
            youtube_video_id=row[1],
            channel_id=row[2],
            title=row[3],
            description=row[4],
            published_at=datetime.fromisoformat(row[5]) if row[5] else None,
            duration_seconds=row[6],
            tags_json=row[7],
            thumbnail_url=row[8],
            last_fetched_at=datetime.fromisoformat(row[9]) if row[9] else None
        )


@dataclass
class VideoSnapshot:
    """Video statistics snapshot"""
    id: Optional[int] = None
    video_id: int = 0
    fetched_at: Optional[datetime] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0

    @classmethod
    def from_db_row(cls, row: tuple) -> 'VideoSnapshot':
        """Create VideoSnapshot from database row"""
        return cls(
            id=row[0],
            video_id=row[1],
            fetched_at=datetime.fromisoformat(row[2]) if row[2] else None,
            view_count=row[3],
            like_count=row[4],
            comment_count=row[5]
        )


@dataclass
class Watchlist:
    """Watchlist for grouping channels"""
    id: Optional[int] = None
    name: str = ""

    @classmethod
    def from_db_row(cls, row: tuple) -> 'Watchlist':
        """Create Watchlist from database row"""
        return cls(id=row[0], name=row[1])


@dataclass
class NicheRun:
    """Niche exploration run"""
    id: Optional[int] = None
    keyword: str = ""
    fetched_at: Optional[datetime] = None
    params_json: str = "{}"

    @property
    def params(self) -> Dict[str, Any]:
        """Parse params from JSON"""
        try:
            return json.loads(self.params_json)
        except:
            return {}

    @classmethod
    def from_db_row(cls, row: tuple) -> 'NicheRun':
        """Create NicheRun from database row"""
        return cls(
            id=row[0],
            keyword=row[1],
            fetched_at=datetime.fromisoformat(row[2]) if row[2] else None,
            params_json=row[3]
        )


@dataclass
class NicheCluster:
    """Niche exploration cluster result"""
    id: Optional[int] = None
    niche_run_id: int = 0
    cluster_index: int = 0
    label: str = ""
    metrics_json: str = "{}"
    sample_videos_json: str = "[]"
    sample_channels_json: str = "[]"

    @property
    def metrics(self) -> Dict[str, Any]:
        """Parse metrics from JSON"""
        try:
            return json.loads(self.metrics_json)
        except:
            return {}

    @property
    def sample_videos(self) -> List[Dict[str, Any]]:
        """Parse sample videos from JSON"""
        try:
            return json.loads(self.sample_videos_json)
        except:
            return []

    @property
    def sample_channels(self) -> List[Dict[str, Any]]:
        """Parse sample channels from JSON"""
        try:
            return json.loads(self.sample_channels_json)
        except:
            return []

    @classmethod
    def from_db_row(cls, row: tuple) -> 'NicheCluster':
        """Create NicheCluster from database row"""
        return cls(
            id=row[0],
            niche_run_id=row[1],
            cluster_index=row[2],
            label=row[3],
            metrics_json=row[4],
            sample_videos_json=row[5],
            sample_channels_json=row[6]
        )
