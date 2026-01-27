"""
YouTube Video Downloader - Standalone Application
독립 실행 가능한 YouTube 영상 다운로더

실행 방법:
    streamlit run youtube_downloader_app.py
"""
import streamlit as st
import os
import tempfile
import subprocess
import json
import zipfile
import re

st.set_page_config(
    page_title="YouTube 다운로더",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
    }
    .feature-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-header'>", unsafe_allow_html=True)
st.title("📥 YouTube 영상 다운로더")
st.markdown("**고화질 영상 다운로드 + AI 장면 분석**")
st.markdown("</div>", unsafe_allow_html=True)

# Initialize session state
if 'download_result' not in st.session_state:
    st.session_state.download_result = None
if 'video_info' not in st.session_state:
    st.session_state.video_info = None

# Input section
st.markdown("---")
col1, col2 = st.columns([4, 1])

with col1:
    video_url = st.text_input(
        "🎬 YouTube 영상 URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="YouTube 영상 URL을 입력하세요"
    )

with col2:
    st.write("")
    st.write("")
    fetch_info = st.button("📊 정보 확인", use_container_width=True, type="secondary")

# Fetch video info
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
                    st.session_state.video_info = json.loads(result.stdout)
                    st.success("✅ 영상 정보를 가져왔습니다!")
                else:
                    st.error("❌ 영상 정보를 가져올 수 없습니다.")
            else:
                st.error("❌ 올바른 YouTube URL을 입력해주세요.")
        except Exception as e:
            st.error(f"❌ 오류 발생: {str(e)}")

# Display video info if available
if st.session_state.video_info:
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
        st.markdown(f"**📌 제목:** {video_info.get('title', 'N/A')}")
        st.markdown(f"**📺 채널:** {video_info.get('channel', 'N/A')}")
        st.markdown(f"**⏱️ 길이:** {video_info.get('duration', 0)} 초")
        st.markdown(f"**👁️ 조회수:** {video_info.get('view_count', 0):,}")

        upload_date = video_info.get('upload_date', '')
        if upload_date and len(upload_date) == 8:
            formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            st.markdown(f"**📅 업로드일:** {formatted_date}")

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
        help="원하는 화질을 선택하세요"
    )

with col2:
    extract_screenshots = st.checkbox(
        "📸 장면별 스크린샷 추출",
        value=False,
        help="AI가 자동으로 장면을 감지하여 스크린샷 추출 (OpenCV 필요)"
    )

# Screenshot options
if extract_screenshots:
    with st.expander("🎨 스크린샷 고급 설정"):
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            scene_threshold = st.slider(
                "장면 감지 민감도",
                min_value=10.0,
                max_value=50.0,
                value=27.0,
                step=1.0,
                help="낮을수록 더 많은 장면을 감지합니다"
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
else:
    scene_threshold = 27.0
    min_scene_duration = 0.5

# Download button
st.markdown("---")

download_button_disabled = not video_url or not video_url.strip()

if st.button(
    "🚀 다운로드 시작",
    type="primary",
    use_container_width=True,
    disabled=download_button_disabled
):
    if not video_url:
        st.error("❌ YouTube URL을 입력해주세요.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        with st.spinner("영상을 다운로드하는 중..."):
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

                    status_text.info(f"📥 다운로드 시작... (선택: {quality_label})")
                    progress_bar.progress(0.1)

                    # Try to extract cookies from browser
                    cookie_extracted = False
                    for browser in ['chrome', 'firefox', 'safari', 'edge']:
                        try:
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
                                status_text.success(f"✅ {browser} 쿠키 추출 성공!")
                                break
                        except:
                            continue

                    if not cookie_extracted:
                        status_text.info("ℹ️ 쿠키 없이 진행 중...")

                    progress_bar.progress(0.2)

                    # Download strategies
                    download_success = False

                    if min_height == 0:
                        format_filter = ''
                    else:
                        format_filter = f'[height>={min_height}]'

                    strategies = [
                        {
                            'name': 'Format 22 (720p)',
                            'format': '22',
                            'use_cookies': True,
                            'min_height': 720
                        },
                        {
                            'name': f'{quality_label} + 쿠키',
                            'format': f'bestvideo{format_filter}+bestaudio/best{format_filter}',
                            'use_cookies': True,
                            'min_height': min_height
                        },
                        {
                            'name': f'{quality_label} (Android)',
                            'format': f'bestvideo{format_filter}+bestaudio',
                            'use_cookies': False,
                            'extra_args': ['--extractor-args', 'youtube:player_client=android'],
                            'min_height': min_height
                        },
                        {
                            'name': '기본 (최선)',
                            'format': 'bestvideo+bestaudio/best',
                            'use_cookies': cookie_extracted,
                            'min_height': 0
                        },
                    ]

                    for idx, strategy in enumerate(strategies):
                        try:
                            if os.path.exists(output_path):
                                os.remove(output_path)

                            status_text.info(f"🔄 {strategy['name']} 시도 중... ({idx+1}/{len(strategies)})")
                            progress_bar.progress(0.2 + (0.5 * (idx / len(strategies))))

                            cmd = [
                                'yt-dlp',
                                '-f', strategy['format'],
                                '-o', output_path,
                                '--merge-output-format', 'mp4',
                            ]

                            if strategy['use_cookies'] and cookie_extracted:
                                cmd.extend(['--cookies', cookies_file])

                            if 'extra_args' in strategy:
                                cmd.extend(strategy['extra_args'])

                            cmd.append(video_url)

                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                timeout=180
                            )

                            if os.path.exists(output_path):
                                file_size = os.path.getsize(output_path)

                                if file_size > 1*1024*1024:  # At least 1MB
                                    download_success = True
                                    video_file = output_path
                                    status_text.success(f"✅ 다운로드 성공! ({file_size/1024/1024:.1f} MB)")
                                    progress_bar.progress(0.7)
                                    break

                        except subprocess.TimeoutExpired:
                            status_text.warning(f"⚠️ {strategy['name']} 타임아웃")
                        except Exception as e:
                            continue

                    if not download_success:
                        raise Exception(
                            f"❌ 다운로드 실패\n\n"
                            f"해결 방법:\n"
                            "1. 더 낮은 화질을 선택해보세요\n"
                            "2. YouTube에 로그인 후 영상을 재생해보세요\n"
                            "3. ffmpeg가 설치되어 있는지 확인하세요\n"
                            "4. yt-dlp를 최신 버전으로 업데이트하세요"
                        )

                    # Read the downloaded file
                    with open(video_file, 'rb') as f:
                        video_bytes = f.read()

                    file_size_mb = len(video_bytes) / (1024*1024)
                    status_text.success(f"💾 파일 크기: {file_size_mb:.2f} MB")

                    # Extract screenshots if requested
                    zip_bytes = None
                    screenshot_count = 0

                    if extract_screenshots:
                        status_text.info("📸 장면별 스크린샷 추출 중...")
                        progress_bar.progress(0.8)

                        try:
                            # Check if scenedetect is available
                            from scenedetect import detect, ContentDetector
                            import cv2

                            # Detect scenes
                            scenes = detect(video_file, ContentDetector(threshold=scene_threshold))

                            # Create scenes directory
                            scenes_dir = os.path.join(temp_dir, "scenes")
                            os.makedirs(scenes_dir, exist_ok=True)

                            # Open video
                            video = cv2.VideoCapture(video_file)
                            fps = video.get(cv2.CAP_PROP_FPS)

                            frames_extracted = []

                            for scene_idx, scene in enumerate(scenes):
                                # Extract start and end frames
                                start_time = scene[0].get_seconds()
                                end_time = scene[1].get_seconds()

                                # Skip scenes that are too short
                                if end_time - start_time < min_scene_duration:
                                    continue

                                # Extract start frame
                                video.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
                                ret, frame = video.read()
                                if ret:
                                    start_filename = f"scene_{scene_idx:03d}_start.jpg"
                                    start_path = os.path.join(scenes_dir, start_filename)
                                    cv2.imwrite(start_path, frame)
                                    frames_extracted.append(start_path)

                                # Extract end frame
                                video.set(cv2.CAP_PROP_POS_MSEC, end_time * 1000)
                                ret, frame = video.read()
                                if ret:
                                    end_filename = f"scene_{scene_idx:03d}_end.jpg"
                                    end_path = os.path.join(scenes_dir, end_filename)
                                    cv2.imwrite(end_path, frame)
                                    frames_extracted.append(end_path)

                            video.release()

                            screenshot_count = len(frames_extracted)

                            if screenshot_count > 0:
                                # Create ZIP
                                zip_path = os.path.join(temp_dir, "screenshots.zip")
                                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                    for frame_path in frames_extracted:
                                        zipf.write(frame_path, arcname=os.path.basename(frame_path))

                                with open(zip_path, 'rb') as f:
                                    zip_bytes = f.read()

                                status_text.success(f"✅ {screenshot_count}개 스크린샷 추출 완료!")
                            else:
                                status_text.warning("⚠️ 스크린샷을 추출하지 못했습니다.")

                        except ImportError:
                            status_text.error("❌ OpenCV 또는 PySceneDetect가 설치되지 않았습니다.")
                            st.caption("설치: pip install opencv-python scenedetect[opencv]")
                        except Exception as e:
                            status_text.error(f"❌ 스크린샷 추출 실패: {str(e)}")

                    progress_bar.progress(1.0)

                    # Store results
                    st.session_state.download_result = {
                        'video_bytes': video_bytes,
                        'video_title': st.session_state.video_info.get('title', 'video') if st.session_state.video_info else 'video',
                        'zip_bytes': zip_bytes,
                        'screenshot_count': screenshot_count
                    }

                    status_text.success("✅ 다운로드 완료!")
                    st.balloons()
                    st.rerun()

            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ 다운로드 실패: {str(e)}")

# Display download buttons if result is available
if st.session_state.download_result:
    st.markdown("---")
    st.subheader("💾 다운로드 완료")

    result = st.session_state.download_result

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 영상 다운로드",
            data=result['video_bytes'],
            file_name=f"{result['video_title'][:50]}.mp4",
            mime="video/mp4",
            use_container_width=True,
            type="primary"
        )
        st.caption(f"크기: {len(result['video_bytes'])/1024/1024:.1f} MB")

    with col2:
        if result['zip_bytes']:
            st.download_button(
                label=f"📦 스크린샷 다운로드 ({result['screenshot_count']}개)",
                data=result['zip_bytes'],
                file_name=f"{result['video_title'][:50]}_screenshots.zip",
                mime="application/zip",
                use_container_width=True
            )
            st.caption(f"크기: {len(result['zip_bytes'])/1024/1024:.1f} MB")
        else:
            st.info("스크린샷 없음")

    if st.button("🔄 새로 다운로드", use_container_width=True):
        st.session_state.download_result = None
        st.session_state.video_info = None
        st.rerun()

# Footer
st.markdown("---")

# Features
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### ✨ 주요 기능
    - 🎥 최대 4K 화질 지원
    - 🤖 AI 장면 자동 감지
    - 📦 일괄 다운로드
    - 🔒 안전한 다운로드
    """)

with col2:
    st.markdown("""
    ### 🛠️ 필수 요구사항
    - **yt-dlp**: `pip install yt-dlp`
    - **ffmpeg**: 고화질 병합용
    - **opencv** (선택): 스크린샷용
    - **scenedetect** (선택): 장면 감지
    """)

with col3:
    st.markdown("""
    ### 💡 사용 팁
    - 브라우저에서 YouTube 로그인
    - 실패 시 낮은 화질 선택
    - 저작권 주의
    - 개인 용도로만 사용
    """)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Made with ❤️ using Streamlit | YouTube Data API</p>
    <p><small>⚠️ 다운로드한 콘텐츠의 저작권은 원 저작자에게 있습니다. 개인 용도로만 사용하세요.</small></p>
</div>
""", unsafe_allow_html=True)
