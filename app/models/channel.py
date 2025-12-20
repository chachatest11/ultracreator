from datetime import datetime
from typing import Optional


class Channel:
    """채널 모델"""

    def __init__(
        self,
        id: Optional[int] = None,
        category_id: int = 1,
        channel_input: str = "",
        channel_id: str = "",
        title: Optional[str] = None,
        subscriber_count: Optional[int] = None,
        country: Optional[str] = None,
        language_hint: Optional[str] = None,
        is_active: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.category_id = category_id
        self.channel_input = channel_input
        self.channel_id = channel_id
        self.title = title
        self.subscriber_count = subscriber_count
        self.country = country
        self.language_hint = language_hint
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "channel_input": self.channel_input,
            "channel_id": self.channel_id,
            "title": self.title,
            "subscriber_count": self.subscriber_count,
            "country": self.country,
            "language_hint": self.language_hint,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_row(cls, row):
        """SQLite row를 Channel 객체로 변환"""
        if not row:
            return None
        return cls(
            id=row[0],
            category_id=row[1],
            channel_input=row[2],
            channel_id=row[3],
            title=row[4],
            subscriber_count=row[5],
            country=row[6],
            language_hint=row[7],
            is_active=row[8],
            created_at=datetime.fromisoformat(row[9]) if row[9] else None,
            updated_at=datetime.fromisoformat(row[10]) if row[10] else None
        )
