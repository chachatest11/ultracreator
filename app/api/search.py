from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict
from ..db import get_db
from ..models import Video
from .downloader import VideoDownloader
import hashlib

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    urls: List[str]  # Xiaohongshu URL 리스트


@router.post("/")
def extract_videos(data: SearchRequest):
    """
    Xiaohongshu URL에서 동영상 정보 추출

    1. 각 URL에서 yt-dlp로 메타데이터 추출
    2. DB에 저장
    3. 결과 반환
    """
    downloader = VideoDownloader()

    # yt-dlp 설치 확인
    if not downloader.check_yt_dlp_installed():
        raise HTTPException(
            status_code=500,
            detail="yt-dlp가 설치되어 있지 않습니다. 'pip install yt-dlp' 명령어로 설치해주세요."
        )

    results = []
    errors = []

    for url in data.urls:
        url = url.strip()
        if not url:
            continue

        try:
            # yt-dlp로 메타데이터 추출
            info = downloader.get_video_info(url)

            if not info:
                errors.append({
                    "url": url,
                    "error": "동영상 정보를 가져올 수 없습니다"
                })
                continue

            # 비디오 ID 생성 (URL 해시 또는 extractor의 ID 사용)
            video_id = info.get('id', hashlib.md5(url.encode()).hexdigest()[:12])

            # 비디오 데이터 구성
            video_data = {
                "video_id": video_id,
                "url": url,
                "title": info.get('title', 'Untitled'),
                "description": info.get('description', ''),
                "thumbnail_url": info.get('thumbnail', ''),
                "duration_seconds": int(info.get('duration', 0)),
                "view_count": int(info.get('view_count', 0)),
                "like_count": int(info.get('like_count', 0)),
                "uploader": info.get('uploader', ''),
                "upload_date": info.get('upload_date', ''),
            }

            # DB에 저장
            with get_db() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                # 기존 영상 확인
                cursor.execute("""
                    SELECT id FROM videos WHERE video_id = ?
                """, (video_id,))
                existing = cursor.fetchone()

                if existing:
                    # UPDATE
                    cursor.execute("""
                        UPDATE videos
                        SET title = ?,
                            url = ?,
                            thumbnail_url = ?,
                            view_count = ?,
                            like_count = ?,
                            updated_at = ?
                        WHERE video_id = ?
                    """, (
                        video_data["title"],
                        url,
                        video_data["thumbnail_url"],
                        video_data["view_count"],
                        video_data["like_count"],
                        now,
                        video_id
                    ))
                else:
                    # INSERT
                    cursor.execute("""
                        INSERT INTO videos (
                            channel_id, video_id, url, title, published_at,
                            view_count, like_count, comment_count, thumbnail_url, duration_seconds,
                            is_short, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video_data.get("uploader", "xiaohongshu"),
                        video_id,
                        url,
                        video_data["title"],
                        video_data.get("upload_date", now),
                        video_data["view_count"],
                        video_data["like_count"],
                        0,  # comment_count
                        video_data["thumbnail_url"],
                        video_data["duration_seconds"],
                        1,  # is_short
                        now,
                        now
                    ))

                conn.commit()

            results.append(video_data)

        except Exception as e:
            errors.append({
                "url": url,
                "error": str(e)
            })

    # DB에서 저장된 영상 조회
    with get_db() as conn:
        cursor = conn.cursor()

        if results:
            video_ids = [r["video_id"] for r in results]
            placeholders = ','.join('?' * len(video_ids))

            cursor.execute(f"""
                SELECT v.id, v.channel_id, v.video_id, v.title, v.published_at,
                       v.view_count, v.like_count, v.comment_count, v.thumbnail_url, v.duration_seconds,
                       v.is_short, v.created_at, v.updated_at, v.channel_id as channel_title
                FROM videos v
                WHERE v.video_id IN ({placeholders})
                ORDER BY v.created_at DESC
            """, video_ids)

            rows = cursor.fetchall()
            videos = [Video.from_row(row).to_dict() for row in rows]
        else:
            videos = []

    return {
        "videos": videos,
        "total": len(videos),
        "errors": errors if errors else None
    }


@router.get("/videos")
def get_videos(
    min_views: int = 0,
    sort: str = "latest"
):
    """
    저장된 영상 조회
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 정렬 조건
        sort_options = {
            "latest": "v.created_at DESC",
            "oldest": "v.created_at ASC",
            "views_desc": "v.view_count DESC",
            "views_asc": "v.view_count ASC",
            "likes_desc": "v.like_count DESC",
            "likes_asc": "v.like_count ASC",
        }
        order_by = sort_options.get(sort, "v.created_at DESC")

        cursor.execute(f"""
            SELECT v.id, v.channel_id, v.video_id, v.title, v.published_at,
                   v.view_count, v.like_count, v.comment_count, v.thumbnail_url, v.duration_seconds,
                   v.is_short, v.created_at, v.updated_at, v.channel_id as channel_title
            FROM videos v
            WHERE v.view_count >= ?
            ORDER BY {order_by}
        """, (min_views,))

        rows = cursor.fetchall()
        videos = [Video.from_row(row).to_dict() for row in rows]

        return {"videos": videos, "total": len(videos)}
