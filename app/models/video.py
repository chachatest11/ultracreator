from datetime import datetime
from typing import Optional


class Video:
    """비디오 모델"""

    def __init__(
        self,
        id: Optional[int] = None,
        channel_id: str = "",
        video_id: str = "",
        title: Optional[str] = None,
        published_at: Optional[datetime] = None,
        view_count: Optional[int] = None,
        thumbnail_url: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        is_short: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        channel_title: Optional[str] = None  # JOIN용 필드
    ):
        self.id = id
        self.channel_id = channel_id
        self.video_id = video_id
        self.title = title
        self.published_at = published_at
        self.view_count = view_count
        self.thumbnail_url = thumbnail_url
        self.duration_seconds = duration_seconds
        self.is_short = is_short
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.channel_title = channel_title

    def to_dict(self):
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "video_id": self.video_id,
            "title": self.title,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "view_count": self.view_count,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "is_short": self.is_short,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "channel_title": self.channel_title
        }

    @classmethod
    def from_row(cls, row):
        """SQLite row를 Video 객체로 변환"""
        if not row:
            return None

        # row 길이에 따라 처리 (JOIN 여부)
        return cls(
            id=row[0],
            channel_id=row[1],
            video_id=row[2],
            title=row[3],
            published_at=datetime.fromisoformat(row[4]) if row[4] else None,
            view_count=row[5],
            thumbnail_url=row[6],
            duration_seconds=row[7],
            is_short=row[8],
            created_at=datetime.fromisoformat(row[9]) if row[9] else None,
            updated_at=datetime.fromisoformat(row[10]) if row[10] else None,
            channel_title=row[11] if len(row) > 11 else None
        )
