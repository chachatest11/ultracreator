from datetime import datetime
from typing import Optional


class ApiKey:
    """API Key 모델"""

    def __init__(
        self,
        id: Optional[int] = None,
        api_key: str = "",
        name: Optional[str] = None,
        is_active: int = 1,
        priority: int = 0,
        quota_exceeded: int = 0,
        last_used_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.api_key = api_key
        self.name = name
        self.is_active = is_active
        self.priority = priority
        self.quota_exceeded = quota_exceeded
        self.last_used_at = last_used_at
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self, mask_key: bool = True):
        """
        딕셔너리로 변환
        mask_key: True면 API 키를 마스킹 처리
        """
        masked_key = None
        if self.api_key:
            if mask_key and len(self.api_key) > 8:
                masked_key = self.api_key[:4] + "..." + self.api_key[-4:]
            else:
                masked_key = self.api_key

        return {
            "id": self.id,
            "api_key": masked_key,
            "name": self.name,
            "is_active": self.is_active,
            "priority": self.priority,
            "quota_exceeded": self.quota_exceeded,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_row(cls, row):
        """SQLite row를 ApiKey 객체로 변환"""
        if not row:
            return None
        return cls(
            id=row[0],
            api_key=row[1],
            name=row[2],
            is_active=row[3],
            priority=row[4],
            quota_exceeded=row[5],
            last_used_at=datetime.fromisoformat(row[6]) if row[6] else None,
            created_at=datetime.fromisoformat(row[7]) if row[7] else None,
            updated_at=datetime.fromisoformat(row[8]) if row[8] else None
        )
