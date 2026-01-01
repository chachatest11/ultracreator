#!/usr/bin/env python3
"""
YouTube 영상 고화질 다운로드 스크립트
사용법: python download_video.py <YouTube_URL>
"""

import subprocess
import sys
import os
import json
import tempfile

def download_youtube_video(video_url, output_filename="video.mp4"):
    """
    YouTube 영상을 고화질로 다운로드
    """
    print(f"📥 영상 다운로드 시작: {video_url}")
    print()

    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        cookies_file = os.path.join(temp_dir, "cookies.txt")
        temp_output = os.path.join(temp_dir, "video.mp4")

        # 1. 쿠키 추출 시도
        print("🍪 브라우저 쿠키 추출 시도...")
        cookie_extracted = False
        for browser in ['chrome', 'firefox', 'safari', 'edge']:
            try:
                print(f"   {browser} 시도 중...", end=" ")
                cookie_cmd = [
                    'yt-dlp',
                    '--cookies-from-browser', browser,
                    '--cookies', cookies_file,
                    '--skip-download',
                    video_url
                ]
                result = subprocess.run(cookie_cmd, capture_output=True, timeout=10)
                if os.path.exists(cookies_file):
                    cookie_extracted = True
                    print(f"✅ 성공!")
                    break
                else:
                    print("실패")
            except:
                print("실패")
                continue

        if not cookie_extracted:
            print("⚠️  쿠키 추출 실패 - 쿠키 없이 진행")
        print()

        # 2. 다운로드 전략들
        strategies = [
            {
                'name': 'Format 22 (720p) + 쿠키',
                'format': '22',
                'use_cookies': True,
                'extra_args': []
            },
            {
                'name': '최고화질 (720p+) + 쿠키',
                'format': 'bestvideo[height>=720]+bestaudio/best[height>=720]',
                'use_cookies': True,
                'extra_args': []
            },
            {
                'name': 'Format 136+140 (720p 어댑티브)',
                'format': '136+140',
                'use_cookies': False,
                'extra_args': ['--extractor-args', 'youtube:player_client=android']
            },
            {
                'name': 'Format 22 + Android',
                'format': '22',
                'use_cookies': False,
                'extra_args': ['--extractor-args', 'youtube:player_client=android']
            },
            {
                'name': '최고화질 + MWEB',
                'format': 'bestvideo[height>=720]+bestaudio/best[height>=720]',
                'use_cookies': False,
                'extra_args': ['--extractor-args', 'youtube:player_client=mweb']
            },
            {
                'name': 'Format 137+140 (1080p 시도)',
                'format': '137+140/136+140',
                'use_cookies': cookie_extracted,
                'extra_args': ['--extractor-args', 'youtube:player_client=android']
            },
            {
                'name': '일반 최고화질',
                'format': 'bestvideo+bestaudio/best',
                'use_cookies': cookie_extracted,
                'extra_args': []
            },
        ]

        # 3. 다운로드 시도
        download_success = False
        for i, strategy in enumerate(strategies, 1):
            try:
                # 이전 다운로드 파일 제거
                if os.path.exists(temp_output):
                    os.remove(temp_output)

                print(f"🔄 전략 {i}/{len(strategies)}: {strategy['name']}")

                # CLI 명령 구성
                cmd = [
                    'yt-dlp',
                    '-f', strategy['format'],
                    '-o', temp_output,
                    '--merge-output-format', 'mp4',
                    '--remote-components', 'ejs:github',  # Enable remote components for JS challenges
                ]

                # 쿠키 추가
                if strategy['use_cookies'] and cookie_extracted:
                    cmd.extend(['--cookies', cookies_file])
                    print("   🍪 브라우저 쿠키 사용")

                # 추가 인자
                cmd.extend(strategy['extra_args'])
                cmd.append(video_url)

                # 명령 표시
                print(f"   명령: {' '.join(cmd[:4])}...")

                # 실행
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180
                )

                # 파일 확인
                if os.path.exists(temp_output):
                    file_size = os.path.getsize(temp_output)
                    file_size_mb = file_size / (1024*1024)

                    # 영상 정보 가져오기
                    try:
                        info_cmd = ['yt-dlp', '-J', video_url]
                        info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
                        info = json.loads(info_result.stdout)
                        height = info.get('height', 0) or 0
                    except:
                        # 파일 크기로 추정
                        height = 720 if file_size > 5*1024*1024 else 360

                    print(f"   📊 파일 크기: {file_size_mb:.1f} MB, 화질: {height}p")

                    # 720p 이상이면 성공
                    if file_size > 5*1024*1024 or height >= 720:
                        download_success = True

                        # 최종 파일로 복사
                        import shutil
                        shutil.copy(temp_output, output_filename)

                        print(f"   ✅ 성공! {height}p ({file_size_mb:.1f} MB)")
                        print()
                        print(f"💾 저장됨: {output_filename}")
                        return True
                    else:
                        print(f"   ⚠️  실패 - 파일 너무 작음 ({file_size_mb:.1f} MB)")
                else:
                    stderr = result.stderr[:200] if result.stderr else result.stdout[:200]
                    print(f"   ⚠️  실패: {stderr}")

                print()

            except subprocess.TimeoutExpired:
                print(f"   ⚠️  타임아웃")
                print()
            except Exception as e:
                print(f"   ⚠️  오류: {str(e)[:150]}")
                print()

        # 모든 전략 실패
        print("❌ 모든 다운로드 전략 실패")
        print()
        print("해결 방법:")
        print("1. 브라우저에서 YouTube에 로그인하고 이 영상을 재생하세요")
        print("2. yt-dlp 업데이트: pip install -U yt-dlp")
        print("3. 다른 영상으로 시도해보세요")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python download_video.py <YouTube_URL> [출력파일명]")
        print()
        print("예시:")
        print("  python download_video.py https://www.youtube.com/watch?v=VIDEO_ID")
        print("  python download_video.py https://www.youtube.com/watch?v=VIDEO_ID my_video.mp4")
        sys.exit(1)

    video_url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "video.mp4"

    success = download_youtube_video(video_url, output_file)
    sys.exit(0 if success else 1)
