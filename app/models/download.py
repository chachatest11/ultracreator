from datetime import datetime
from typing import Optional


class Download:
    """다운로드 모델"""

    def __init__(
        self,
        id: Optional[int] = None,
        video_id: str = "",
        status: str = "queued",  # queued/running/done/failed
        file_path: Optional[str] = None,
        error_message: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.video_id = video_id
        self.status = status
        self.file_path = file_path
        self.error_message = error_message
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "status": self.status,
            "file_path": self.file_path,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_row(cls, row):
        """SQLite row를 Download 객체로 변환"""
        if not row:
            return None
        return cls(
            id=row[0],
            video_id=row[1],
            status=row[2],
            file_path=row[3],
            error_message=row[4],
            created_at=datetime.fromisoformat(row[5]) if row[5] else None,
            updated_at=datetime.fromisoformat(row[6]) if row[6] else None
        )
