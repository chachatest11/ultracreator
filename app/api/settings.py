from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from ..db import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str


@router.get("/{key}")
def get_setting(key: str):
    """설정값 조회"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT key, value, updated_at
            FROM settings
            WHERE key = ?
        """, (key,))
        row = cursor.fetchone()

        if not row:
            return {"key": key, "value": None}

        return {
            "key": row[0],
            "value": row[1],
            "updated_at": row[2]
        }


@router.put("/{key}")
def update_setting(key: str, data: SettingUpdate):
    """설정값 저장/업데이트"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, data.value, now))

        conn.commit()

        return {
            "key": key,
            "value": data.value,
            "updated_at": now
        }


@router.delete("/{key}")
def delete_setting(key: str):
    """설정값 삭제"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()

        return {"success": True, "message": "설정이 삭제되었습니다"}
