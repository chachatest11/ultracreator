"""
Channel Detail - Detailed Channel Analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import tempfile
import glob
import yt_dlp
import zipfile
import subprocess
import json
import re
from core import db, metrics, similar, jobs
from core.scene_extractor import extract_scenes, get_scene_summary

st.set_page_config(page_title="📈 상세 분석", page_icon="📈", layout="wide")


# Video player dialog
@st.dialog("🎬 영상 재생", width="large")
def show_video_player(video_id, video_title):
    """Display video player in a dialog"""
    st.markdown(f"**{video_title}**")

    # YouTube video player
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    st.video(video_url)

    # Download options
    st.markdown("---")
    st.subheader("📥 다운로드 옵션")

    extract_screenshots = st.checkbox(
        "📸 장면별 스크린샷 추출 (AI 영상 제작용)",
        value=False,
        help="각 장면(컷)의 시작과 끝 프레임을 자동 추출합니다"
    )

    if extract_screenshots:
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

    st.markdown("---")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("📥 영상 다운로드" + (" + 스크린샷 추출" if extract_screenshots else ""), width="stretch", type="primary"):
            with st.spinner("영상을 다운로드하는 중... (시간이 걸릴 수 있습니다)"):
                try:
                    # Create temporary directory
                    with tempfile.TemporaryDirectory() as temp_dir:
                        output_path = os.path.join(temp_dir, "video.mp4")
                        cookies_file = os.path.join(temp_dir, "cookies.txt")

                        st.info("📥 고화질 다운로드 시작... (CLI 직접 실행)")

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

                        # Strategy list with CLI commands
                        strategies = [
                            # Strategy 1: Format 22 with cookies
                            {
                                'name': 'Format 22 (720p) + 쿠키',
                                'format': '22',
                                'use_cookies': True,
                                'extra_args': []
                            },
                            # Strategy 2: Best quality >= 720p with cookies
                            {
                                'name': '최고화질 (720p+) + 쿠키',
                                'format': 'bestvideo[height>=720]+bestaudio/best[height>=720]',
                                'use_cookies': True,
                                'extra_args': []
                            },
                            # Strategy 3: Format 136+140 (720p adaptive)
                            {
                                'name': 'Format 136+140 (720p 어댑티브)',
                                'format': '136+140',
                                'use_cookies': False,
                                'extra_args': ['--extractor-args', 'youtube:player_client=android']
                            },
                            # Strategy 4: Format 22 with android client
                            {
                                'name': 'Format 22 + Android',
                                'format': '22',
                                'use_cookies': False,
                                'extra_args': ['--extractor-args', 'youtube:player_client=android']
                            },
                            # Strategy 5: Best with mweb
                            {
                                'name': '최고화질 + MWEB',
                                'format': 'bestvideo[height>=720]+bestaudio/best[height>=720]',
                                'use_cookies': False,
                                'extra_args': ['--extractor-args', 'youtube:player_client=mweb']
                            },
                            # Strategy 6: Format 137+140 (1080p)
                            {
                                'name': 'Format 137+140 (1080p 시도)',
                                'format': '137+140/136+140',
                                'use_cookies': cookie_extracted,
                                'extra_args': ['--extractor-args', 'youtube:player_client=android']
                            },
                            # Strategy 7: Generic best
                            {
                                'name': '일반 최고화질',
                                'format': 'bestvideo+bestaudio/best',
                                'use_cookies': cookie_extracted,
                                'extra_args': []
                            },
                        ]

                        for strategy in strategies:
                            try:
                                # Remove previous downloads
                                if os.path.exists(output_path):
                                    os.remove(output_path)

                                st.info(f"🔄 시도 중: {strategy['name']}")

                                # Build CLI command (use yt-dlp directly, not python -m)
                                cmd = [
                                    'yt-dlp',
                                    '-f', strategy['format'],
                                    '-o', output_path,
                                    '--merge-output-format', 'mp4',
                                    '--remote-components', 'ejs:github',  # Enable remote components for JS challenges
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

                                    # Accept if file is large enough (likely 720p+)
                                    if file_size > 5*1024*1024 or height >= 720:
                                        download_success = True
                                        video_file = output_path
                                        st.success(f"✅ {strategy['name']} 성공! {height}p ({file_size/1024/1024:.1f} MB)")
                                        break
                                    else:
                                        st.warning(f"⚠️ {strategy['name']} 실패 - 파일 너무 작음 ({file_size/1024/1024:.1f} MB)")
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
                            raise Exception(
                                "❌ 고화질 다운로드 실패\n\n"
                                "7가지 전략을 모두 시도했지만 720p 이상 화질을 다운로드할 수 없습니다.\n\n"
                                "해결 방법:\n"
                                "1. 브라우저에서 YouTube에 로그인하고 이 영상을 한 번 재생하세요\n"
                                "2. yt-dlp 업데이트: pip install -U yt-dlp\n"
                                "3. 다른 영상으로 시도해보세요\n\n"
                                "YouTube의 2025년 보안 강화로 일부 영상은 다운로드가 제한될 수 있습니다."
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
                                    threshold=scene_threshold if extract_screenshots else 27.0,
                                    min_scene_len=min_scene_duration if extract_screenshots else 0.5,
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

                                    # Provide ZIP download button
                                    st.download_button(
                                        label=f"📦 스크린샷 다운로드 ({screenshot_result['total_frames']}개 이미지)",
                                        data=zip_bytes,
                                        file_name=f"{video_title[:50]}_screenshots.zip",
                                        mime="application/zip",
                                        width="stretch"
                                    )

                                else:
                                    st.warning(screenshot_result.get('message', '스크린샷 추출 실패'))

                            except Exception as e:
                                st.error(f"스크린샷 추출 실패: {str(e)}")
                                st.caption("💡 OpenCV와 PySceneDetect가 설치되어 있는지 확인하세요:")
                                st.code("pip install opencv-python scenedetect")

                        st.markdown("---")

                        # Provide video download button
                        st.download_button(
                            label="💾 영상 다운로드 - 저장하기",
                            data=video_bytes,
                            file_name=f"{video_title[:50]}.mp4",
                            mime="video/mp4",
                            width="stretch"
                        )
                        st.success("✅ 다운로드 완료! 위 버튼을 클릭하여 저장하세요.")

                except Exception as e:
                    st.error(f"다운로드 실패: {str(e)}")
                    st.caption("💡 문제 해결 방법:")
                    st.caption("1. **ffmpeg 필요**: 고화질 다운로드를 위해 ffmpeg가 필요합니다.")
                    st.caption("   - Linux: `sudo apt-get install ffmpeg`")
                    st.caption("   - macOS: `brew install ffmpeg`")
                    st.caption("   - Windows: https://ffmpeg.org/download.html")
                    st.caption("2. 일부 영상은 YouTube 정책상 다운로드가 제한될 수 있습니다.")
                    st.caption("3. 오디오만 제공되는 영상이거나 라이브 스트림일 수 있습니다.")

    with col2:
        if st.button("❌ 닫기", width="stretch"):
            st.rerun()


st.title("📈 상세 분석")
st.markdown("채널 상세 분석 및 영상 데이터")

# Get all channels for selector
channels = db.get_all_channels()

if not channels:
    st.warning("등록된 채널이 없습니다. Dashboard에서 채널을 추가해주세요.")
    st.stop()

# Channel selector
channel_names = [ch.title for ch in channels]

# Check if channel was selected from dashboard
selected_index = 0
if 'selected_channel_id' in st.session_state:
    for i, ch in enumerate(channels):
        if ch.id == st.session_state.selected_channel_id:
            selected_index = i
            break

selected_channel_name = st.selectbox(
    "채널 선택",
    channel_names,
    index=selected_index
)

selected_channel = channels[channel_names.index(selected_channel_name)]

# Get channel metrics
channel_metrics = metrics.get_channel_metrics(selected_channel.id)

# Channel header
col1, col2 = st.columns([1, 4])

with col1:
    if selected_channel.thumbnail_url:
        st.image(selected_channel.thumbnail_url, width=150)

with col2:
    st.header(selected_channel.title)
    if selected_channel.handle:
        st.markdown(f"**핸들:** @{selected_channel.handle}")
    st.markdown(f"**채널 ID:** `{selected_channel.youtube_channel_id}`")
    if selected_channel.last_fetched_at:
        st.caption(f"마지막 갱신: {selected_channel.last_fetched_at.strftime('%Y-%m-%d %H:%M')}")

st.markdown("---")

# Key metrics
st.subheader("📊 주요 지표")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "구독자",
        f"{channel_metrics['subscriber_count']:,}",
        delta=channel_metrics['growth_30d']['subscriber_growth']
    )

with col2:
    st.metric(
        "총 조회수",
        f"{channel_metrics['view_count']:,}",
        delta=channel_metrics['growth_30d']['view_growth']
    )

with col3:
    st.metric(
        "영상 수",
        f"{channel_metrics['video_count']:,}"
    )

with col4:
    st.metric(
        "평균 조회수 (10개)",
        f"{int(channel_metrics['avg_views_recent_10']):,}"
    )

# Detailed metrics
st.markdown("---")
st.subheader("📈 상세 분석")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 업로드 패턴")

    upload_freq = channel_metrics['upload_frequency']
    st.metric("평균 업로드 주기", f"{upload_freq['average_days']:.1f}일")
    st.metric("중앙값 업로드 주기", f"{upload_freq['median_days']:.1f}일")

    upload_patterns = channel_metrics['upload_patterns']
    st.markdown(f"**가장 많이 올리는 요일:** {upload_patterns['most_common_day']}")
    st.markdown(f"**가장 많이 올리는 시간:** {upload_patterns['most_common_hour']}시 (KST)")

with col2:
    st.markdown("#### 조회수 분산")

    view_var = channel_metrics['view_variance']
    st.metric("분산 계수 (CV)", f"{view_var['cv']:.2f}")
    st.metric("채널 유형", view_var['type'])
    st.caption("CV < 0.5: 안정형 (조회수 안정) | CV ≥ 0.5: 한방형 (특정 영상 집중)")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Shorts 분석")

    shorts_metrics = channel_metrics['shorts_metrics']
    st.metric("Shorts 비중 (≤60초)", f"{shorts_metrics['shorts_ratio'] * 100:.1f}%")

    st.markdown("**길이 분포:**")
    st.markdown(f"- 30초 이하: {shorts_metrics['under_30s'] * 100:.1f}%")
    st.markdown(f"- 31~60초: {shorts_metrics['31_to_60s'] * 100:.1f}%")
    st.markdown(f"- 61초 이상: {shorts_metrics['over_60s'] * 100:.1f}%")

with col2:
    st.markdown("#### 기타 지표")

    st.metric("평균 제목 길이", f"{channel_metrics['avg_title_length']:.1f}자")
    st.metric("Top5 조회수 집중도", f"{channel_metrics['top5_concentration'] * 100:.1f}%")
    st.caption("상위 5개 영상이 전체 조회수에서 차지하는 비중")

# Recent videos
st.markdown("---")
st.subheader("🎬 최근 영상")

# Video count selector
col1, col2 = st.columns([2, 6])
with col1:
    video_limit = st.number_input(
        "표시할 영상 수",
        min_value=10,
        max_value=200,
        value=50,
        step=10,
        help="최근 영상을 몇 개까지 표시할지 설정합니다"
    )

videos = db.get_videos_by_channel(selected_channel.id, limit=video_limit)

if not videos:
    st.info("이 채널의 영상 데이터가 없습니다.")
else:
    # Display videos in grid with thumbnails
    st.markdown(f"**총 {len(videos)}개의 영상**")

    # Create grid layout (5 columns)
    cols_per_row = 5
    for i in range(0, len(videos), cols_per_row):
        cols = st.columns(cols_per_row)

        for j in range(cols_per_row):
            idx = i + j
            if idx < len(videos):
                video = videos[idx]
                snapshot = db.get_latest_video_snapshot(video.id)

                with cols[j]:
                    # Thumbnail - clickable
                    thumbnail_url = video.thumbnail_url or f"https://img.youtube.com/vi/{video.youtube_video_id}/hqdefault.jpg"

                    st.image(thumbnail_url, width="stretch")

                    # Clickable thumbnail button
                    if st.button(
                        "▶️ 재생",
                        key=f"play_{video.youtube_video_id}",
                        width="stretch"
                    ):
                        show_video_player(video.youtube_video_id, video.title)

                    # Video info
                    st.markdown(f"**{video.title[:40]}{'...' if len(video.title) > 40 else ''}**")

                    # Stats
                    video_type = "🩳 Shorts" if video.duration_seconds <= 60 else "🎥 일반"
                    st.caption(f"{video_type} | {video.duration_seconds}초")

                    if snapshot:
                        st.caption(f"👁️ {snapshot.view_count:,}")
                        st.caption(f"👍 {snapshot.like_count:,}")
                        st.caption(f"💬 {snapshot.comment_count:,}")

                    st.caption(f"📅 {video.published_at.strftime('%Y-%m-%d') if video.published_at else 'N/A'}")
                    st.markdown("---")

    # Summary table view (collapsible)
    with st.expander("📋 전체 영상 목록 (테이블 형식)"):
        video_data = []

        for video in videos:
            snapshot = db.get_latest_video_snapshot(video.id)

            video_data.append({
                "제목": video.title,
                "게시일": video.published_at.strftime("%Y-%m-%d %H:%M") if video.published_at else "N/A",
                "길이 (초)": video.duration_seconds,
                "유형": "Shorts" if video.duration_seconds <= 60 else "일반",
                "조회수": snapshot.view_count if snapshot else 0,
                "좋아요": snapshot.like_count if snapshot else 0,
                "댓글": snapshot.comment_count if snapshot else 0,
                "참여율": (
                    f"{((snapshot.like_count + snapshot.comment_count) / snapshot.view_count * 100):.2f}%"
                    if snapshot and snapshot.view_count > 0 else "0.00%"
                )
            })

        df = pd.DataFrame(video_data)

        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            column_config={
                "조회수": st.column_config.NumberColumn(format="%d"),
                "좋아요": st.column_config.NumberColumn(format="%d"),
                "댓글": st.column_config.NumberColumn(format="%d")
            }
        )

    # Visualization
    st.markdown("---")
    st.subheader("📊 조회수 분포")

    # Create dataframe for visualization
    viz_data = []
    for video in videos:
        snapshot = db.get_latest_video_snapshot(video.id)
        viz_data.append({
            "제목": video.title,
            "게시일": video.published_at.strftime("%Y-%m-%d %H:%M") if video.published_at else "N/A",
            "게시일_dt": video.published_at if video.published_at else None,
            "유형": "Shorts" if video.duration_seconds <= 60 else "일반",
            "조회수": snapshot.view_count if snapshot else 0,
        })

    df_viz = pd.DataFrame(viz_data)

    col1, col2 = st.columns(2)

    with col1:
        # View count distribution
        fig = px.histogram(
            df_viz,
            x="조회수",
            nbins=20,
            title="조회수 분포",
            labels={"조회수": "조회수", "count": "영상 수"}
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        # Views by video type
        type_views = df_viz.groupby("유형")["조회수"].sum().reset_index()
        fig = px.pie(
            type_views,
            values="조회수",
            names="유형",
            title="유형별 총 조회수"
        )
        st.plotly_chart(fig, width="stretch")

    # Timeline chart
    st.markdown("#### 시간별 조회수 추이")

    # Filter out None values
    df_viz_filtered = df_viz[df_viz['게시일_dt'].notna()].copy()
    df_sorted = df_viz_filtered.sort_values('게시일_dt')

    fig = go.Figure()

    # Separate shorts and regular videos
    shorts_df = df_sorted[df_sorted['유형'] == 'Shorts']
    regular_df = df_sorted[df_sorted['유형'] == '일반']

    if not shorts_df.empty:
        fig.add_trace(go.Scatter(
            x=shorts_df['게시일_dt'],
            y=shorts_df['조회수'],
            mode='markers+lines',
            name='Shorts',
            marker=dict(size=8, color='red')
        ))

    if not regular_df.empty:
        fig.add_trace(go.Scatter(
            x=regular_df['게시일_dt'],
            y=regular_df['조회수'],
            mode='markers+lines',
            name='일반 영상',
            marker=dict(size=8, color='blue')
        ))

    fig.update_layout(
        xaxis_title="게시일",
        yaxis_title="조회수",
        hovermode='x unified'
    )

    st.plotly_chart(fig, width="stretch")

    # Upload pattern charts
    st.markdown("---")
    st.subheader("📅 업로드 패턴")

    col1, col2 = st.columns(2)

    upload_patterns = channel_metrics['upload_patterns']

    with col1:
        # Day of week distribution
        if upload_patterns['day_distribution']:
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_data = {day: upload_patterns['day_distribution'].get(day, 0) * 100
                       for day in day_order}

            fig = px.bar(
                x=list(day_data.keys()),
                y=list(day_data.values()),
                title="요일별 업로드 비율",
                labels={"x": "요일", "y": "비율 (%)"}
            )
            st.plotly_chart(fig, width="stretch")

    with col2:
        # Hour distribution
        if upload_patterns['hour_distribution']:
            hours = sorted(upload_patterns['hour_distribution'].keys())
            percentages = [upload_patterns['hour_distribution'][h] * 100 for h in hours]

            fig = px.bar(
                x=hours,
                y=percentages,
                title="시간대별 업로드 비율 (KST)",
                labels={"x": "시간 (시)", "y": "비율 (%)"}
            )
            st.plotly_chart(fig, width="stretch")

# Similar Channels
st.markdown("---")
st.subheader("🔗 유사 채널 찾기")
st.markdown("이 채널의 인기 영상 제목에서 키워드를 추출하여 YouTube 검색 결과에 자주 나타나는 유사한 채널을 찾습니다.")

# Initialize session state
if 'similar_channels_data' not in st.session_state:
    st.session_state.similar_channels_data = None
if 'similar_channels_loading' not in st.session_state:
    st.session_state.similar_channels_loading = False

col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    top_videos_count = st.number_input(
        "분석할 인기 영상 수",
        min_value=5,
        max_value=30,
        value=10,
        help="상위 N개의 인기 영상을 분석합니다"
    )

with col2:
    related_per_video = st.number_input(
        "영상당 검색 결과 수",
        min_value=10,
        max_value=50,
        value=20,
        help="각 영상의 키워드로 검색할 결과 수"
    )

with col3:
    min_appearances = st.number_input(
        "최소 출현 횟수",
        min_value=1,
        max_value=10,
        value=2,
        help="채널이 몇 번 이상 출현해야 결과에 포함할지 설정 (높을수록 신뢰도 높음)"
    )

col1, col2 = st.columns([1, 5])

with col1:
    if st.button("🔍 유사 채널 찾기", type="primary", width="stretch"):
        st.session_state.similar_channels_loading = True
        st.session_state.similar_channels_data = None

if st.session_state.similar_channels_loading:
    with st.spinner("유사 채널을 찾는 중... (시간이 걸릴 수 있습니다)"):
        try:
            result = similar.find_similar_channels(
                channel_id=selected_channel.youtube_channel_id,
                top_videos_count=top_videos_count,
                related_per_video=related_per_video,
                min_appearances=min_appearances
            )
            st.session_state.similar_channels_data = result
            st.session_state.similar_channels_loading = False
            st.rerun()
        except Exception as e:
            st.error(f"유사 채널을 찾는 중 오류가 발생했습니다: {e}")
            st.session_state.similar_channels_loading = False

# Display results
if st.session_state.similar_channels_data is not None:
    result = st.session_state.similar_channels_data
    similar_channels = result.get("channels", [])
    debug_info = result.get("debug_info", {})

    # Show debug information
    if debug_info:
        with st.expander("🔍 분석 상세 정보", expanded=not similar_channels):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("채널 발견", "✅" if debug_info.get("channel_found") else "❌")
                st.metric("영상 수", debug_info.get("videos_count", 0))
                st.metric("스냅샷 있는 영상", debug_info.get("videos_with_snapshots", 0))

            with col2:
                st.metric("분석한 인기 영상", debug_info.get("top_videos_analyzed", 0))
                st.metric("수집한 검색 결과", debug_info.get("total_related_videos", 0))

            with col3:
                st.metric("발견한 유니크 채널", debug_info.get("unique_channels_found", 0))
                st.metric("필터 후 채널", debug_info.get("channels_after_filter", 0))

            # Show errors
            if debug_info.get("errors"):
                st.markdown("**⚠️ 문제점:**")
                for error in debug_info["errors"]:
                    st.warning(error)

    if not similar_channels:
        if not debug_info.get("errors"):
            st.info("유사 채널을 찾지 못했습니다. 영상 데이터가 부족하거나 관련 채널이 없을 수 있습니다.")
    else:
        st.success(f"✅ {len(similar_channels)}개의 유사 채널을 발견했습니다!")

        # Sort options
        col1, col2 = st.columns([2, 6])
        with col1:
            sort_option = st.selectbox(
                "정렬 기준",
                ["신뢰도 순", "구독자 수 순", "영상 수 순", "출현 횟수 순"],
                key="similar_channels_sort"
            )

        # Sort channels based on selected option
        if sort_option == "구독자 수 순":
            similar_channels_sorted = sorted(similar_channels, key=lambda x: x['subscriber_count'], reverse=True)
        elif sort_option == "영상 수 순":
            similar_channels_sorted = sorted(similar_channels, key=lambda x: x['video_count'], reverse=True)
        elif sort_option == "출현 횟수 순":
            similar_channels_sorted = sorted(similar_channels, key=lambda x: x['appearance_count'], reverse=True)
        else:  # 신뢰도 순 (기본)
            similar_channels_sorted = sorted(similar_channels, key=lambda x: x['confidence_score'], reverse=True)

        # Display similar channels
        for i, ch in enumerate(similar_channels_sorted):
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 2])

                with col1:
                    if ch.get('thumbnail_url'):
                        st.image(ch['thumbnail_url'], width=100)

                with col2:
                    # Create YouTube channel URL
                    handle = ch.get('handle', '')
                    # Remove leading @ if present for consistent handling
                    handle_clean = handle.lstrip('@') if handle else ''

                    if handle_clean:
                        youtube_url = f"https://www.youtube.com/@{handle_clean}"
                    else:
                        youtube_url = f"https://www.youtube.com/channel/{ch['channel_id']}"

                    st.markdown(f"### {i+1}. [{ch['title']}]({youtube_url})")
                    if handle_clean:
                        # Display handle with add button
                        col_handle, col_add_btn = st.columns([5, 1])
                        with col_handle:
                            st.markdown(f"**핸들:** [@{handle_clean}](https://www.youtube.com/@{handle_clean})")
                        with col_add_btn:
                            # Check if channel already exists
                            existing = db.get_channel_by_youtube_id(ch['channel_id'])
                            if not existing:
                                if st.button("➕", key=f"add_{ch['channel_id']}", help="Dashboard에 채널 추가", width="stretch"):
                                    with st.spinner(f"{ch['title']} 채널을 추가하는 중..."):
                                        result = jobs.fetch_channel_data(
                                            ch['channel_id'],
                                            force_refresh=False,
                                            progress_callback=lambda msg: None
                                        )
                                        if result:
                                            st.success(f"✅ '{ch['title']}' 채널이 추가되었습니다!")
                                            st.rerun()
                                        else:
                                            st.error("채널 추가에 실패했습니다.")
                            else:
                                st.caption("✓")
                    st.caption(f"**채널 ID:** `{ch['channel_id']}`")

                    # Display stats
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("구독자", f"{ch['subscriber_count']:,}")
                    with col_b:
                        st.metric("영상 수", f"{ch['video_count']:,}")
                    with col_c:
                        st.metric("출현 횟수", f"{ch['appearance_count']}회")

                with col3:
                    st.markdown("**유사도**")
                    st.progress(ch['confidence_score'] / 100)
                    st.caption(f"{ch['confidence_score']}% 신뢰도")

                    # Action buttons
                    if st.button("📊 채널 분석", key=f"analyze_{ch['channel_id']}", width="stretch"):
                        # Check if channel already exists in database
                        existing = db.get_channel_by_youtube_id(ch['channel_id'])
                        if existing:
                            st.session_state.selected_channel_id = existing.id
                            st.rerun()
                        else:
                            st.info("이 채널을 먼저 Dashboard에서 추가해주세요.")

                st.markdown("---")

        # Export option
        st.markdown("#### 📥 결과 내보내기")

        export_data = [{
            "순위": i + 1,
            "채널명": ch['title'],
            "핸들": ch.get('handle', ''),
            "채널 ID": ch['channel_id'],
            "구독자": ch['subscriber_count'],
            "영상 수": ch['video_count'],
            "출현 횟수": ch['appearance_count'],
            "신뢰도 (%)": ch['confidence_score']
        } for i, ch in enumerate(similar_channels_sorted)]

        df_export = pd.DataFrame(export_data)
        csv = df_export.to_csv(index=False, encoding='utf-8-sig')

        st.download_button(
            label="📥 CSV로 다운로드",
            data=csv,
            file_name=f"similar_channels_{selected_channel.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=False
        )

# Footer
st.markdown("---")
st.caption("💡 팁: 이 페이지에서 채널의 모든 세부 정보를 확인할 수 있습니다.")
