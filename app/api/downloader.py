import os
import subprocess
import json
import hashlib
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


class VideoDownloader:
    """yt-dlp를 사용한 Xiaohongshu 비디오 다운로더"""

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        Path(download_dir).mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        """파일명에서 특수문자 제거"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        return filename

    def _extract_video_id(self, url: str) -> str:
        """URL에서 비디오 ID 추출 (해시 사용)"""
        # Xiaohongshu URL에서 ID 추출 시도
        # 예: https://www.xiaohongshu.com/explore/xxxxx
        # 또는 https://xhslink.com/xxxxx
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        if len(path_parts) > 0 and path_parts[-1]:
            return path_parts[-1]

        # 추출 실패 시 URL 해시 사용
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def download_video(
        self,
        url: str,
        custom_name: Optional[str] = None
    ) -> Dict:
        """
        단일 비디오 다운로드

        Args:
            url: Xiaohongshu 동영상 URL
            custom_name: 커스텀 파일명 (선택)

        Returns:
            {
                "success": bool,
                "file_path": str or None,
                "error_message": str or None
            }
        """
        try:
            video_id = self._extract_video_id(url)

            # 출력 파일명 결정
            if custom_name:
                safe_name = self._sanitize_filename(custom_name)
                filename = f"{safe_name}.mp4"
            else:
                filename = f"{video_id}.mp4"

            output_path = os.path.join(self.download_dir, filename)

            # yt-dlp 명령어
            command = [
                "yt-dlp",
                # 비디오+오디오 병합, 최대 가능한 해상도
                "-f", "best",
                # 병합 출력 형식을 MP4로 지정
                "--merge-output-format", "mp4",
                # 출력 파일 경로
                "-o", output_path,
                # User-Agent 설정
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                url
            ]

            # 실행
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "file_path": output_path,
                    "error_message": None
                }
            else:
                return {
                    "success": False,
                    "file_path": None,
                    "error_message": result.stderr or "다운로드 실패"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "file_path": None,
                "error_message": "다운로드 시간 초과 (5분)"
            }
        except Exception as e:
            return {
                "success": False,
                "file_path": None,
                "error_message": str(e)
            }

    def check_yt_dlp_installed(self) -> bool:
        """yt-dlp 설치 여부 확인"""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_video_info(self, url: str) -> Optional[Dict]:
        """비디오 정보 가져오기 (yt-dlp 사용)"""
        try:
            command = [
                "yt-dlp",
                "--dump-json",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "--no-warnings",
                url
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            return None

        except Exception as e:
            print(f"Error getting video info: {e}")
            return None
