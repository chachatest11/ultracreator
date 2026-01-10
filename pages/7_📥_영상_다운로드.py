"""
Video Downloader - Download videos from YouTube, TikTok, Instagram, Baidu
"""
import streamlit as st
import yt_dlp
import os
import tempfile
import re
from urllib.parse import urlparse

st.set_page_config(page_title="📥 영상 다운로드", page_icon="📥", layout="wide")

st.title("📥 영상 다운로드")
st.markdown("YouTube, TikTok, Instagram, Baidu에서 동영상을 다운로드합니다.")

# Platform detection function
def detect_platform(url: str) -> str:
    """Detect platform from URL"""
    url_lower = url.lower()

    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'YouTube'
    elif 'tiktok.com' in url_lower:
        return 'TikTok'
    elif 'instagram.com' in url_lower:
        return 'Instagram'
    elif 'baidu.com' in url_lower:
        return 'Baidu'
    else:
        return 'Unknown'


# URL input
st.subheader("🔗 동영상 URL")
video_url = st.text_input(
    "URL을 입력하세요",
    placeholder="https://www.youtube.com/watch?v=...",
    help="YouTube, TikTok, Instagram, Baidu 동영상 URL을 입력하세요"
)

if video_url:
    # Detect platform
    platform = detect_platform(video_url)

    if platform != 'Unknown':
        st.success(f"✅ 감지된 플랫폼: **{platform}**")
    else:
        st.warning("⚠️ 지원하지 않는 플랫폼입니다. YouTube, TikTok, Instagram, Baidu만 지원됩니다.")
        st.stop()

    st.markdown("---")

    # Quality selection
    st.subheader("🎨 화질 선택")
    quality_option = st.radio(
        "원하는 화질을 선택하세요",
        options=["720p", "1080p", "최고화질"],
        horizontal=True,
        help="선택한 화질 이상으로 다운로드됩니다"
    )

    st.markdown("---")

    # Download button
    if st.button("📥 다운로드 시작", type="primary", use_container_width=True):
        with st.spinner("영상 정보를 가져오는 중..."):
            try:
                # Configure yt-dlp options based on quality
                if quality_option == "720p":
                    format_option = "bestvideo[height<=720]+bestaudio/best[height<=720]"
                elif quality_option == "1080p":
                    format_option = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
                else:  # 최고화질
                    format_option = "bestvideo+bestaudio/best"

                # Create temporary directory for download
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

                    ydl_opts = {
                        'format': format_option,
                        'outtmpl': output_template,
                        'merge_output_format': 'mp4',  # Merge to mp4
                        'postprocessors': [{
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': 'mp4',
                        }],
                        'quiet': False,
                        'no_warnings': False,
                        'progress_hooks': [],
                    }

                    # Platform-specific options
                    if platform == 'TikTok':
                        ydl_opts['http_headers'] = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                    elif platform == 'Instagram':
                        ydl_opts['http_headers'] = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }

                    # Progress display
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def progress_hook(d):
                        if d['status'] == 'downloading':
                            # Extract percentage
                            percent_str = d.get('_percent_str', '0%').strip('%')
                            try:
                                percent = float(percent_str)
                                progress_bar.progress(min(int(percent), 100) / 100)
                                status_text.text(f"다운로드 중... {percent:.1f}%")
                            except:
                                pass
                        elif d['status'] == 'finished':
                            progress_bar.progress(100)
                            status_text.text("다운로드 완료! 파일을 처리하는 중...")

                    ydl_opts['progress_hooks'].append(progress_hook)

                    # Download video
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(video_url, download=True)
                        video_title = info.get('title', 'video')

                        # Find downloaded file
                        downloaded_files = [f for f in os.listdir(temp_dir) if f.endswith('.mp4')]

                        if downloaded_files:
                            video_file_path = os.path.join(temp_dir, downloaded_files[0])

                            # Read file
                            with open(video_file_path, 'rb') as f:
                                video_bytes = f.read()

                            status_text.empty()
                            progress_bar.empty()

                            st.success(f"✅ 다운로드 완료: **{video_title}**")

                            # Video info
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("파일 크기", f"{len(video_bytes) / (1024*1024):.1f} MB")
                            with col2:
                                st.metric("해상도", f"{info.get('width', 'N/A')}x{info.get('height', 'N/A')}")
                            with col3:
                                duration = info.get('duration', 0)
                                st.metric("길이", f"{int(duration // 60)}분 {int(duration % 60)}초")

                            st.markdown("---")

                            # Download button
                            st.download_button(
                                label="💾 파일 다운로드",
                                data=video_bytes,
                                file_name=f"{video_title}.mp4",
                                mime="video/mp4",
                                use_container_width=True
                            )

                            # Video preview
                            st.markdown("### 🎬 미리보기")
                            st.video(video_bytes)
                        else:
                            st.error("❌ 다운로드한 파일을 찾을 수 없습니다.")

            except Exception as e:
                st.error(f"❌ 다운로드 중 오류가 발생했습니다: {str(e)}")
                st.info("💡 팁: URL이 올바른지 확인하고, 해당 동영상이 공개 상태인지 확인해주세요.")

else:
    # Show instructions
    st.info("📌 위에 동영상 URL을 입력하여 시작하세요")

    st.markdown("---")
    st.markdown("### 📖 사용 방법")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **지원 플랫폼:**
        - 🎥 YouTube (youtube.com, youtu.be)
        - 🎵 TikTok (tiktok.com)
        - 📸 Instagram (instagram.com)
        - 🔍 Baidu (baidu.com)
        """)

    with col2:
        st.markdown("""
        **화질 옵션:**
        - 📱 720p (HD)
        - 🖥️ 1080p (Full HD)
        - 🎬 최고화질 (사용 가능한 최고 화질)
        """)

    st.markdown("---")
    st.markdown("""
    **💡 참고사항:**
    - 모든 동영상은 비디오+오디오가 통합된 MP4 파일로 다운로드됩니다.
    - 다운로드 시간은 영상 길이와 화질에 따라 달라질 수 있습니다.
    - 저작권이 있는 콘텐츠는 개인적인 용도로만 사용하세요.
    """)
