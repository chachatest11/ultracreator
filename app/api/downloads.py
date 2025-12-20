from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
from typing import List
import os
from ..db import get_db
from ..models import Download
from .downloader import VideoDownloader

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

# 다운로더 인스턴스
downloader = VideoDownloader(download_dir="downloads")


class DownloadStartRequest(BaseModel):
    video_ids: List[str]


@router.post("/start")
def start_downloads(data: DownloadStartRequest):
    """
    선택한 영상들 다운로드 시작

    간단 구현: 순차적으로 다운로드하고 결과 반환
    """
    if not data.video_ids:
        raise HTTPException(status_code=400, detail="다운로드할 영상이 없습니다")

    # yt-dlp 설치 확인
    if not downloader.check_yt_dlp_installed():
        raise HTTPException(
            status_code=500,
            detail="yt-dlp가 설치되어 있지 않습니다. 'pip install yt-dlp' 또는 'brew install yt-dlp'로 설치하세요."
        )

    results = []

    for video_id in data.video_ids:
        # 영상 정보 조회 (채널명 가져오기)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.video_id, v.title, c.title as channel_title
                FROM videos v
                LEFT JOIN channels c ON v.channel_id = c.channel_id
                WHERE v.video_id = ?
            """, (video_id,))
            video_row = cursor.fetchone()

        if not video_row:
            results.append({
                "video_id": video_id,
                "status": "failed",
                "error": "영상 정보를 찾을 수 없습니다"
            })
            continue

        video_id_db = video_row[0]
        video_title = video_row[1]
        channel_title = video_row[2]

        # downloads 테이블에 기록
        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # 다운로드 상태 초기화
            cursor.execute("""
                INSERT INTO downloads (video_id, status, created_at, updated_at)
                VALUES (?, 'running', ?, ?)
            """, (video_id, now, now))
            download_id = cursor.lastrowid
            conn.commit()

        # 실제 다운로드 수행
        result = downloader.download_video(video_id, channel_title)

        # 결과 업데이트
        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            if result["success"]:
                cursor.execute("""
                    UPDATE downloads
                    SET status = 'done',
                        file_path = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (result["file_path"], now, download_id))
                status = "done"
                error = None
            else:
                cursor.execute("""
                    UPDATE downloads
                    SET status = 'failed',
                        error_message = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (result["error_message"], now, download_id))
                status = "failed"
                error = result["error_message"]

            conn.commit()

        results.append({
            "video_id": video_id,
            "video_title": video_title,
            "status": status,
            "file_path": result.get("file_path"),
            "error": error
        })

    success_count = len([r for r in results if r["status"] == "done"])
    failed_count = len([r for r in results if r["status"] == "failed"])

    return {
        "total": len(results),
        "success": success_count,
        "failed": failed_count,
        "results": results
    }


@router.get("/status")
def get_download_status(video_ids: str = ""):
    """다운로드 상태 조회"""
    if not video_ids:
        return {"downloads": []}

    video_id_list = video_ids.split(",")

    with get_db() as conn:
        cursor = conn.cursor()

        placeholders = ",".join(["?" for _ in video_id_list])
        cursor.execute(f"""
            SELECT id, video_id, status, file_path, error_message,
                   created_at, updated_at
            FROM downloads
            WHERE video_id IN ({placeholders})
            ORDER BY created_at DESC
        """, video_id_list)

        rows = cursor.fetchall()
        downloads = [Download.from_row(row).to_dict() for row in rows]

        return {"downloads": downloads}


@router.get("/file/{video_id}")
def download_file(video_id: str):
    """완료된 파일 다운로드"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT file_path, status
            FROM downloads
            WHERE video_id = ? AND status = 'done'
            ORDER BY created_at DESC
            LIMIT 1
        """, (video_id,))
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="다운로드된 파일을 찾을 수 없습니다")

    file_path = row[0]

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=f"{video_id}.mp4"
    )


@router.get("/history")
def get_download_history(limit: int = 100):
    """다운로드 히스토리 조회"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, video_id, status, file_path, error_message,
                   created_at, updated_at
            FROM downloads
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        downloads = [Download.from_row(row).to_dict() for row in rows]

        return {"downloads": downloads, "total": len(downloads)}
