"""
YouTube Video Downloader - Standalone video download tool
"""
import streamlit as st
import os
import tempfile
import subprocess
import json
import zipfile
import re
from core.scene_extractor import extract_scenes, get_scene_summary

st.set_page_config(page_title="📥 영상 다운로더", page_icon="📥", layout="wide")

st.title("📥 YouTube 영상 다운로더")
st.markdown("YouTube 영상을 고화질로 다운로드하고 장면별 스크린샷을 추출하세요")

# Initialize session state
if 'download_result' not in st.session_state:
    st.session_state.download_result = None

# Input section
st.subheader("🎬 영상 정보 입력")

col1, col2 = st.columns([3, 1])

with col1:
    video_url = st.text_input(
        "YouTube 영상 URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="YouTube 영상 URL을 입력하세요"
    )

with col2:
    st.write("")
    st.write("")
    fetch_info = st.button("📊 영상 정보 확인", use_container_width=True)

# Fetch video info
video_info = None
if fetch_info and video_url:
    with st.spinner("영상 정보를 가져오는 중..."):
        try:
            # Extract video ID
            video_id_match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', video_url)
            if video_id_match:
                video_id = video_id_match.group(1)

                # Get video info using yt-dlp
                info_cmd = ['yt-dlp', '-J', video_url]
                result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    video_info = json.loads(result.stdout)
                    st.session_state.video_info = video_info
                    st.success("✅ 영상 정보를 가져왔습니다!")
                else:
                    st.error("영상 정보를 가져올 수 없습니다.")
            else:
                st.error("올바른 YouTube URL을 입력해주세요.")
        except Exception as e:
            st.error(f"오류 발생: {str(e)}")

# Display video info if available
if 'video_info' in st.session_state:
    video_info = st.session_state.video_info

    st.markdown("---")
    st.subheader("📋 영상 정보")

    col1, col2 = st.columns([1, 2])

    with col1:
        # Thumbnail
        thumbnail_url = video_info.get('thumbnail', '')
        if thumbnail_url:
            st.image(thumbnail_url, use_column_width=True)

    with col2:
        st.markdown(f"**제목:** {video_info.get('title', 'N/A')}")
        st.markdown(f"**채널:** {video_info.get('channel', 'N/A')}")
        st.markdown(f"**길이:** {video_info.get('duration', 0)} 초")
        st.markdown(f"**조회수:** {video_info.get('view_count', 0):,}")

        upload_date = video_info.get('upload_date', '')
        if upload_date and len(upload_date) == 8:
            formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            st.markdown(f"**업로드일:** {formatted_date}")

# Download settings
st.markdown("---")
st.subheader("⚙️ 다운로드 설정")

col1, col2 = st.columns([1, 1])

with col1:
    quality_option = st.selectbox(
        "🎥 화질 선택",
        options=[
            "자동 (최고화질)",
            "2160p (4K)",
            "1440p (2K)",
            "1080p (Full HD)",
            "720p (HD)",
            "480p",
            "360p"
        ],
        index=0,
        help="원하는 화질을 선택하세요. 선택한 화질 이상으로 다운로드됩니다."
    )

with col2:
    extract_screenshots = st.checkbox(
        "📸 장면별 스크린샷 추출 (AI 영상 제작용)",
        value=False,
        help="각 장면(컷)의 시작과 끝 프레임을 자동 추출합니다"
    )

if extract_screenshots:
    st.markdown("#### 스크린샷 추출 옵션")
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        scene_threshold = st.slider(
            "장면 감지 민감도",
            min_value=10.0,
            max_value=50.0,
            value=27.0,
            step=1.0,
            help="낮을수록 더 많은 장면을 감지합니다 (기본: 27)"
        )
    with col_opt2:
        min_scene_duration = st.slider(
            "최소 장면 길이 (초)",
            min_value=0.1,
            max_value=3.0,
            value=0.5,
            step=0.1,
            help="이보다 짧은 장면은 무시합니다"
        )

# Download button
st.markdown("---")

if st.button("📥 다운로드 시작", type="primary", use_container_width=True, disabled=not video_url):
    if not video_url:
        st.error("YouTube URL을 입력해주세요.")
    else:
        with st.spinner("영상을 다운로드하는 중... (시간이 걸릴 수 있습니다)"):
            try:
                # Create temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_path = os.path.join(temp_dir, "video.mp4")
                    cookies_file = os.path.join(temp_dir, "cookies.txt")

                    # Parse quality selection
                    quality_map = {
                        "자동 (최고화질)": {"height": 0, "label": "최고화질"},
                        "2160p (4K)": {"height": 2160, "label": "2160p"},
                        "1440p (2K)": {"height": 1440, "label": "1440p"},
                        "1080p (Full HD)": {"height": 1080, "label": "1080p"},
                        "720p (HD)": {"height": 720, "label": "720p"},
                        "480p": {"height": 480, "label": "480p"},
                        "360p": {"height": 360, "label": "360p"}
                    }
                    selected_quality = quality_map[quality_option]
                    min_height = selected_quality["height"]
                    quality_label = selected_quality["label"]

                    st.info(f"📥 다운로드 시작... (선택: {quality_label})")

                    # Try to extract cookies from browser first
                    cookie_extracted = False
                    for browser in ['chrome', 'firefox', 'safari', 'edge']:
                        try:
                            st.caption(f"🍪 {browser} 쿠키 추출 시도...")
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
                                st.success(f"✅ {browser} 쿠키 추출 성공!")
                                break
                        except:
                            continue

                    if not cookie_extracted:
                        st.caption("⚠️ 브라우저 쿠키 추출 실패 - 쿠키 없이 진행")

                    # Download strategies using CLI
                    download_success = False

                    # Build format strings based on selected quality
                    if min_height == 0:
                        # Auto - best quality
                        format_filter = ''
                        format_desc = '최고화질'
                    else:
                        # Specific quality
                        format_filter = f'[height>={min_height}]'
                        format_desc = f'{min_height}p 이상'

                    # Strategy list with CLI commands (adjusted for selected quality)
                    strategies = [
                        # Strategy 1: Format 22 with cookies (720p)
                        {
                            'name': f'Format 22 (720p) + 쿠키',
                            'format': '22',
                            'use_cookies': True,
                            'extra_args': [],
                            'min_height': 720
                        },
                        # Strategy 2: Best quality with selected filter + cookies
                        {
                            'name': f'{format_desc} + 쿠키',
                            'format': f'bestvideo{format_filter}+bestaudio/best{format_filter}',
                            'use_cookies': True,
                            'extra_args': [],
                            'min_height': min_height
                        },
                        # Strategy 3: Adaptive formats with android
                        {
                            'name': f'{format_desc} 어댑티브 (Android)',
                            'format': f'bestvideo{format_filter}+bestaudio',
                            'use_cookies': False,
                            'extra_args': ['--extractor-args', 'youtube:player_client=android'],
                            'min_height': min_height
                        },
                        # Strategy 4: Format 22 with android client
                        {
                            'name': 'Format 22 + Android',
                            'format': '22',
                            'use_cookies': False,
                            'extra_args': ['--extractor-args', 'youtube:player_client=android'],
                            'min_height': 720
                        },
                        # Strategy 5: Best with mweb
                        {
                            'name': f'{format_desc} + MWEB',
                            'format': f'bestvideo{format_filter}+bestaudio/best{format_filter}',
                            'use_cookies': False,
                            'extra_args': ['--extractor-args', 'youtube:player_client=mweb'],
                            'min_height': min_height
                        },
                        # Strategy 6: Specific format IDs (1080p/720p)
                        {
                            'name': 'Format 137/136 (1080p/720p 시도)',
                            'format': '137+140/136+140',
                            'use_cookies': cookie_extracted,
                            'extra_args': ['--extractor-args', 'youtube:player_client=android'],
                            'min_height': 720
                        },
                        # Strategy 7: Generic best
                        {
                            'name': f'{format_desc} (기본)',
                            'format': f'bestvideo{format_filter}+bestaudio/best{format_filter}' if format_filter else 'bestvideo+bestaudio/best',
                            'use_cookies': cookie_extracted,
                            'extra_args': [],
                            'min_height': min_height
                        },
                    ]

                    for strategy in strategies:
                        try:
                            # Remove previous downloads
                            if os.path.exists(output_path):
                                os.remove(output_path)

                            st.info(f"🔄 시도 중: {strategy['name']}")

                            # Build CLI command
                            cmd = [
                                'yt-dlp',
                                '-f', strategy['format'],
                                '-o', output_path,
                                '--merge-output-format', 'mp4',
                            ]

                            # Add cookies if available and needed
                            if strategy['use_cookies'] and cookie_extracted:
                                cmd.extend(['--cookies', cookies_file])
                                st.caption("🍪 브라우저 쿠키 사용")

                            # Add extra args
                            cmd.extend(strategy['extra_args'])

                            # Add URL
                            cmd.append(video_url)

                            # Show command for debugging
                            st.caption(f"🔧 명령: {' '.join(cmd[:4])}...")

                            # Execute
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                timeout=180
                            )

                            # Check if file exists and get info
                            if os.path.exists(output_path):
                                file_size = os.path.getsize(output_path)

                                # Get video info
                                info_cmd = [
                                    'yt-dlp',
                                    '-J',
                                    video_url
                                ]

                                try:
                                    info_result = subprocess.run(
                                        info_cmd,
                                        capture_output=True,
                                        text=True,
                                        timeout=30
                                    )
                                    info = json.loads(info_result.stdout)
                                    height = info.get('height', 0) or 0
                                except:
                                    # Fallback: check file size
                                    # 720p video should be at least 5MB for short videos
                                    height = 720 if file_size > 5*1024*1024 else 360

                                st.caption(f"📊 파일 크기: {file_size/1024/1024:.1f} MB, 예상 화질: {height}p")

                                # Check if quality meets user's selection
                                strategy_min_height = strategy.get('min_height', 0)
                                required_height = max(strategy_min_height, min_height) if min_height > 0 else strategy_min_height

                                # For auto mode, accept if file is reasonable size
                                # For specific quality, check height
                                if min_height == 0:
                                    # Auto mode - accept if file size is reasonable
                                    if file_size > 5*1024*1024 or height >= 360:
                                        download_success = True
                                        video_file = output_path
                                        st.success(f"✅ {strategy['name']} 성공! {height}p ({file_size/1024/1024:.1f} MB)")
                                        break
                                else:
                                    # Specific quality selected
                                    if height >= required_height or (height == 0 and file_size > 10*1024*1024):
                                        download_success = True
                                        video_file = output_path
                                        st.success(f"✅ {strategy['name']} 성공! {height}p ({file_size/1024/1024:.1f} MB)")
                                        break
                                    else:
                                        st.warning(f"⚠️ {strategy['name']} 실패 - {height}p (요구: {required_height}p 이상)")
                                        os.remove(output_path)
                            else:
                                stderr = result.stderr[:300] if result.stderr else result.stdout[:300] if result.stdout else 'unknown'
                                st.warning(f"⚠️ {strategy['name']} 실패: {stderr}")

                        except subprocess.TimeoutExpired:
                            st.warning(f"⚠️ {strategy['name']} 타임아웃")
                        except Exception as e:
                            st.warning(f"⚠️ {strategy['name']} 오류: {str(e)[:150]}")
                            continue

                    if not download_success:
                        quality_msg = f"{quality_label}" if min_height > 0 else "고화질"
                        raise Exception(
                            f"❌ {quality_msg} 다운로드 실패\n\n"
                            f"7가지 전략을 모두 시도했지만 선택한 화질({quality_label})로 다운로드할 수 없습니다.\n\n"
                            "해결 방법:\n"
                            "1. 더 낮은 화질을 선택해보세요 (예: 480p 또는 360p)\n"
                            "2. 브라우저에서 YouTube에 로그인하고 이 영상을 한 번 재생하세요\n"
                            "3. yt-dlp 업데이트: pip install -U yt-dlp\n"
                            "4. 다른 영상으로 시도해보세요\n\n"
                            "참고: 일부 영상은 원본 화질이 낮거나 YouTube 제한이 있을 수 있습니다."
                        )

                    # Get file size
                    file_size = os.path.getsize(video_file)
                    file_size_mb = file_size / (1024*1024)

                    st.info(f"💾 최종 파일 크기: {file_size_mb:.2f} MB")

                    # Read the downloaded file
                    with open(video_file, 'rb') as f:
                        video_bytes = f.read()

                    # Extract screenshots if requested
                    screenshot_result = None
                    if extract_screenshots:
                        st.markdown("---")
                        st.info("📸 장면별 스크린샷 추출 중...")

                        progress_placeholder = st.empty()

                        def update_progress(msg):
                            progress_placeholder.info(msg)

                        # Create scenes directory
                        scenes_dir = os.path.join(temp_dir, "scenes")

                        try:
                            screenshot_result = extract_scenes(
                                video_path=video_file,
                                output_dir=scenes_dir,
                                threshold=scene_threshold,
                                min_scene_len=min_scene_duration,
                                progress_callback=update_progress
                            )

                            progress_placeholder.empty()

                            if screenshot_result['success']:
                                st.success(f"✅ {screenshot_result['total_frames']}개 프레임 추출 완료!")

                                # Display summary
                                with st.expander("📊 장면 분석 결과 보기"):
                                    st.markdown(get_scene_summary(screenshot_result))

                                # Create ZIP file with screenshots
                                zip_path = os.path.join(temp_dir, "screenshots.zip")
                                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                    for frame_info in screenshot_result['frames']:
                                        zipf.write(
                                            frame_info['path'],
                                            arcname=os.path.basename(frame_info['path'])
                                        )

                                # Read ZIP file
                                with open(zip_path, 'rb') as f:
                                    zip_bytes = f.read()

                                # Store in session state
                                st.session_state.download_result = {
                                    'video_bytes': video_bytes,
                                    'video_title': video_info.get('title', 'video') if 'video_info' in st.session_state else 'video',
                                    'zip_bytes': zip_bytes,
                                    'screenshot_count': screenshot_result['total_frames']
                                }

                            else:
                                st.warning(screenshot_result.get('message', '스크린샷 추출 실패'))

                        except Exception as e:
                            st.error(f"스크린샷 추출 실패: {str(e)}")
                            st.caption("💡 OpenCV와 PySceneDetect가 설치되어 있는지 확인하세요:")
                            st.code("pip install opencv-python scenedetect")
                    else:
                        # No screenshots - just store video
                        st.session_state.download_result = {
                            'video_bytes': video_bytes,
                            'video_title': video_info.get('title', 'video') if 'video_info' in st.session_state else 'video',
                            'zip_bytes': None,
                            'screenshot_count': 0
                        }

                    st.success("✅ 다운로드 완료!")
                    st.rerun()

            except Exception as e:
                st.error(f"다운로드 실패: {str(e)}")
                st.caption("💡 문제 해결 방법:")
                st.caption("1. **ffmpeg 필요**: 고화질 다운로드를 위해 ffmpeg가 필요합니다.")
                st.caption("   - Linux: `sudo apt-get install ffmpeg`")
                st.caption("   - macOS: `brew install ffmpeg`")
                st.caption("   - Windows: https://ffmpeg.org/download.html")
                st.caption("2. 일부 영상은 YouTube 정책상 다운로드가 제한될 수 있습니다.")
                st.caption("3. 오디오만 제공되는 영상이거나 라이브 스트림일 수 있습니다.")

# Display download buttons if result is available
if st.session_state.download_result:
    st.markdown("---")
    st.subheader("💾 다운로드")

    result = st.session_state.download_result

    col1, col2 = st.columns(2)

    with col1:
        # Video download button
        st.download_button(
            label="📥 영상 다운로드",
            data=result['video_bytes'],
            file_name=f"{result['video_title'][:50]}.mp4",
            mime="video/mp4",
            use_container_width=True,
            type="primary"
        )

    with col2:
        # Screenshots download button (if available)
        if result['zip_bytes']:
            st.download_button(
                label=f"📦 스크린샷 다운로드 ({result['screenshot_count']}개)",
                data=result['zip_bytes'],
                file_name=f"{result['video_title'][:50]}_screenshots.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.info("스크린샷 없음")

# Help section
st.markdown("---")
with st.expander("❓ 사용 방법 및 도움말"):
    st.markdown("""
    ### 📖 사용 방법

    1. **YouTube URL 입력**
       - 영상 페이지의 URL을 복사하여 붙여넣기
       - 예: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`

    2. **영상 정보 확인** (선택사항)
       - "📊 영상 정보 확인" 버튼을 클릭하여 영상 정보 미리보기

    3. **화질 선택**
       - 원하는 화질을 선택 (높은 화질일수록 용량이 큼)
       - "자동"은 가능한 최고 화질로 다운로드

    4. **스크린샷 추출** (선택사항)
       - AI 영상 제작용으로 각 장면의 스크린샷 추출
       - 장면 감지 민감도와 최소 길이 조절 가능

    5. **다운로드**
       - "📥 다운로드 시작" 버튼 클릭
       - 완료 후 영상과 스크린샷(선택 시) 저장

    ---

    ### 🛠️ 필수 요구사항

    - **yt-dlp**: YouTube 다운로더
      ```bash
      pip install yt-dlp
      ```

    - **ffmpeg**: 고화질 영상 병합용
      ```bash
      # Linux
      sudo apt-get install ffmpeg

      # macOS
      brew install ffmpeg

      # Windows
      # https://ffmpeg.org/download.html
      ```

    - **스크린샷 추출 (선택사항)**
      ```bash
      pip install opencv-python scenedetect
      ```

    ---

    ### ⚠️ 주의사항

    - 일부 영상은 저작권 보호로 다운로드가 제한될 수 있습니다
    - 고화질 영상은 용량이 크므로 충분한 저장 공간 필요
    - 다운로드한 영상의 저작권은 원 저작자에게 있습니다
    - 개인 용도로만 사용하세요

    ---

    ### 💡 팁

    - 브라우저에서 YouTube에 로그인하면 다운로드 성공률이 높아집니다
    - 화질이 낮게 다운로드되면 더 낮은 화질 옵션을 선택해보세요
    - 스크린샷 추출은 시간이 걸릴 수 있습니다 (영상 길이에 비례)
    """)

# Footer
st.markdown("---")
st.caption("💡 팁: 고화질 다운로드를 위해서는 ffmpeg가 설치되어 있어야 합니다!")
