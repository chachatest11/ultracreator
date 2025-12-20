from datetime import datetime
from typing import Optional


class Category:
    """카테고리(채널 그룹) 모델"""

    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.name = name
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_row(cls, row):
        """SQLite row를 Category 객체로 변환"""
        if not row:
            return None
        return cls(
            id=row[0],
            name=row[1],
            created_at=datetime.fromisoformat(row[2]) if row[2] else None
        )
