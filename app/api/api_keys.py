from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from ..db import get_db
from ..models.api_key import ApiKey

router = APIRouter(prefix="/api/api_keys", tags=["api_keys"])


class ApiKeyCreate(BaseModel):
    api_key: str
    name: Optional[str] = None
    priority: int = 0


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[int] = None
    priority: Optional[int] = None


@router.get("/")
def get_api_keys():
    """모든 API 키 조회 (키는 마스킹)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, api_key, name, is_active, priority, quota_exceeded,
                   last_used_at, created_at, updated_at
            FROM api_keys
            ORDER BY priority ASC, created_at ASC
        """)
        rows = cursor.fetchall()
        api_keys = [ApiKey.from_row(row).to_dict(mask_key=True) for row in rows]
        return {"api_keys": api_keys}


@router.post("/")
def create_api_key(data: ApiKeyCreate):
    """새 API 키 추가"""
    if not data.api_key.strip():
        raise HTTPException(status_code=400, detail="API 키는 필수입니다")

    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        try:
            cursor.execute("""
                INSERT INTO api_keys (api_key, name, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (data.api_key.strip(), data.name, data.priority, now, now))
            conn.commit()

            api_key_id = cursor.lastrowid

            # 생성된 API 키 조회
            cursor.execute("""
                SELECT id, api_key, name, is_active, priority, quota_exceeded,
                       last_used_at, created_at, updated_at
                FROM api_keys
                WHERE id = ?
            """, (api_key_id,))
            row = cursor.fetchone()
            api_key_obj = ApiKey.from_row(row)

            return {"api_key": api_key_obj.to_dict(mask_key=True)}

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(status_code=400, detail="이미 존재하는 API 키입니다")
            raise HTTPException(status_code=500, detail=str(e))


@router.put("/{api_key_id}")
def update_api_key(api_key_id: int, data: ApiKeyUpdate):
    """API 키 정보 수정"""
    with get_db() as conn:
        cursor = conn.cursor()

        # API 키 존재 확인
        cursor.execute("SELECT id FROM api_keys WHERE id = ?", (api_key_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="API 키를 찾을 수 없습니다")

        # 업데이트할 필드 구성
        updates = []
        params = []

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)

        if data.is_active is not None:
            updates.append("is_active = ?")
            params.append(data.is_active)

        if data.priority is not None:
            updates.append("priority = ?")
            params.append(data.priority)

        if not updates:
            raise HTTPException(status_code=400, detail="업데이트할 내용이 없습니다")

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(api_key_id)

        cursor.execute(f"""
            UPDATE api_keys
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        conn.commit()

        # 수정된 API 키 조회
        cursor.execute("""
            SELECT id, api_key, name, is_active, priority, quota_exceeded,
                   last_used_at, created_at, updated_at
            FROM api_keys
            WHERE id = ?
        """, (api_key_id,))
        row = cursor.fetchone()
        api_key_obj = ApiKey.from_row(row)

        return {"api_key": api_key_obj.to_dict(mask_key=True)}


@router.delete("/{api_key_id}")
def delete_api_key(api_key_id: int):
    """API 키 삭제"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM api_keys WHERE id = ?", (api_key_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="API 키를 찾을 수 없습니다")

        cursor.execute("DELETE FROM api_keys WHERE id = ?", (api_key_id,))
        conn.commit()

        return {"success": True, "message": "API 키가 삭제되었습니다"}


@router.post("/{api_key_id}/reset_quota")
def reset_quota(api_key_id: int):
    """API 키의 쿼터 초과 상태 초기화"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE api_keys
            SET quota_exceeded = 0, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), api_key_id))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="API 키를 찾을 수 없습니다")

        return {"success": True, "message": "쿼터 상태가 초기화되었습니다"}


@router.post("/reset_all_quotas")
def reset_all_quotas():
    """모든 API 키의 쿼터 초과 상태 초기화 (매일 자정 실행용)"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            UPDATE api_keys
            SET quota_exceeded = 0, updated_at = ?
            WHERE quota_exceeded = 1
        """, (now,))
        conn.commit()

        return {
            "success": True,
            "message": f"{cursor.rowcount}개의 API 키 쿼터가 초기화되었습니다"
        }


@router.get("/active")
def get_active_api_key():
    """사용 가능한 API 키 가져오기 (우선순위순, 쿼터 초과되지 않은 것)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, api_key, name, is_active, priority, quota_exceeded,
                   last_used_at, created_at, updated_at
            FROM api_keys
            WHERE is_active = 1 AND quota_exceeded = 0
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        """)
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="사용 가능한 API 키가 없습니다. 새 API 키를 추가하거나 쿼터를 초기화하세요."
            )

        api_key_obj = ApiKey.from_row(row)

        # last_used_at 업데이트
        cursor.execute("""
            UPDATE api_keys
            SET last_used_at = ?, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), datetime.now().isoformat(), api_key_obj.id))
        conn.commit()

        # 실제 API 키 반환 (마스킹 안함)
        return {"api_key": api_key_obj.to_dict(mask_key=False)}


@router.post("/{api_key_id}/mark_quota_exceeded")
def mark_quota_exceeded(api_key_id: int):
    """API 키를 쿼터 초과 상태로 표시"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE api_keys
            SET quota_exceeded = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), api_key_id))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="API 키를 찾을 수 없습니다")

        return {"success": True, "message": "API 키가 쿼터 초과 상태로 표시되었습니다"}
