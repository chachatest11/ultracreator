from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from ..db import get_db
from ..models import Channel
from .youtube import YouTubeAPI

router = APIRouter(prefix="/api/channels", tags=["channels"])


class BulkUpsertRequest(BaseModel):
    category_id: int
    channel_inputs: List[str]
    api_key: str


@router.get("/")
def get_channels(category_id: Optional[int] = None):
    """채널 목록 조회"""
    with get_db() as conn:
        cursor = conn.cursor()
        if category_id:
            cursor.execute("""
                SELECT id, category_id, channel_input, channel_id, title,
                       subscriber_count, country, language_hint, is_active,
                       created_at, updated_at
                FROM channels
                WHERE category_id = ?
                ORDER BY created_at DESC
            """, (category_id,))
        else:
            cursor.execute("""
                SELECT id, category_id, channel_input, channel_id, title,
                       subscriber_count, country, language_hint, is_active,
                       created_at, updated_at
                FROM channels
                ORDER BY created_at DESC
            """)
        rows = cursor.fetchall()
        channels = [Channel.from_row(row).to_dict() for row in rows]
        return {"channels": channels}


@router.post("/bulk_upsert")
def bulk_upsert_channels(data: BulkUpsertRequest):
    """
    채널 일괄 저장/업데이트

    1. 각 채널 입력을 channelId로 정규화
    2. YouTube API로 채널 정보 가져오기
    3. DB에 upsert (없으면 INSERT, 있으면 UPDATE)
    """
    if not data.api_key:
        raise HTTPException(status_code=400, detail="YouTube API Key가 필요합니다")

    if not data.channel_inputs:
        raise HTTPException(status_code=400, detail="채널 입력이 비어있습니다")

    youtube_api = YouTubeAPI(data.api_key)
    results = []
    errors = []

    for channel_input in data.channel_inputs:
        channel_input = channel_input.strip()
        if not channel_input:
            continue

        try:
            # 1. channelId 정규화
            channel_id = youtube_api.normalize_channel_input(channel_input)
            if not channel_id:
                errors.append({
                    "input": channel_input,
                    "error": "채널 ID를 찾을 수 없습니다"
                })
                continue

            # 2. 채널 정보 가져오기
            channel_info = youtube_api.get_channel_info(channel_id)
            if not channel_info:
                errors.append({
                    "input": channel_input,
                    "error": "채널 정보를 가져올 수 없습니다"
                })
                continue

            # 3. DB에 upsert
            with get_db() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                # 기존 채널 확인
                cursor.execute("""
                    SELECT id FROM channels
                    WHERE category_id = ? AND channel_id = ?
                """, (data.category_id, channel_id))
                existing = cursor.fetchone()

                if existing:
                    # UPDATE
                    cursor.execute("""
                        UPDATE channels
                        SET title = ?,
                            subscriber_count = ?,
                            country = ?,
                            updated_at = ?
                        WHERE category_id = ? AND channel_id = ?
                    """, (
                        channel_info["title"],
                        channel_info["subscriber_count"],
                        channel_info.get("country"),
                        now,
                        data.category_id,
                        channel_id
                    ))
                    action = "updated"
                else:
                    # INSERT
                    cursor.execute("""
                        INSERT INTO channels (
                            category_id, channel_input, channel_id, title,
                            subscriber_count, country, is_active,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """, (
                        data.category_id,
                        channel_input,
                        channel_id,
                        channel_info["title"],
                        channel_info["subscriber_count"],
                        channel_info.get("country"),
                        now,
                        now
                    ))
                    action = "created"

                conn.commit()

                results.append({
                    "input": channel_input,
                    "channel_id": channel_id,
                    "title": channel_info["title"],
                    "action": action
                })

        except Exception as e:
            errors.append({
                "input": channel_input,
                "error": str(e)
            })

    return {
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.put("/{channel_id}/toggle_active")
def toggle_channel_active(channel_id: int):
    """채널 활성/비활성 토글"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 현재 상태 확인
        cursor.execute("SELECT is_active FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="채널을 찾을 수 없습니다")

        current_status = row[0]
        new_status = 0 if current_status == 1 else 1

        # 상태 업데이트
        cursor.execute("""
            UPDATE channels
            SET is_active = ?, updated_at = ?
            WHERE id = ?
        """, (new_status, datetime.now().isoformat(), channel_id))
        conn.commit()

        return {
            "success": True,
            "channel_id": channel_id,
            "is_active": new_status
        }


@router.delete("/{channel_id}")
def delete_channel(channel_id: int):
    """채널 삭제"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM channels WHERE id = ?", (channel_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="채널을 찾을 수 없습니다")

        cursor.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        conn.commit()

        return {"success": True, "message": "채널이 삭제되었습니다"}
