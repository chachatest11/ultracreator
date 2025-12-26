"""
Channel Detail - Detailed Channel Analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from core import db, metrics, similar

st.set_page_config(page_title="Channel Detail", page_icon="🔍", layout="wide")

st.title("🔍 Channel Detail")
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
st.subheader("🎬 최근 영상 (50개)")

videos = db.get_videos_by_channel(selected_channel.id, limit=50)

if not videos:
    st.info("이 채널의 영상 데이터가 없습니다.")
else:
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
        use_container_width=True,
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

    col1, col2 = st.columns(2)

    with col1:
        # View count distribution
        fig = px.histogram(
            df,
            x="조회수",
            nbins=20,
            title="조회수 분포",
            labels={"조회수": "조회수", "count": "영상 수"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Views by video type
        type_views = df.groupby("유형")["조회수"].sum().reset_index()
        fig = px.pie(
            type_views,
            values="조회수",
            names="유형",
            title="유형별 총 조회수"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Timeline chart
    st.markdown("#### 시간별 조회수 추이")

    df['게시일_dt'] = pd.to_datetime(df['게시일'])
    df_sorted = df.sort_values('게시일_dt')

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

    st.plotly_chart(fig, use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)

# Similar Channels
st.markdown("---")
st.subheader("🔗 유사 채널 찾기")
st.markdown("이 채널의 인기 영상에서 YouTube 관련 영상 알고리즘을 분석하여 유사한 채널을 찾습니다.")

# Initialize session state
if 'similar_channels_data' not in st.session_state:
    st.session_state.similar_channels_data = None
if 'similar_channels_loading' not in st.session_state:
    st.session_state.similar_channels_loading = False

col1, col2, col3 = st.columns([2, 2, 4])

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
        "영상당 관련 영상 수",
        min_value=10,
        max_value=50,
        value=20,
        help="각 영상당 가져올 관련 영상의 수"
    )

col1, col2 = st.columns([1, 5])

with col1:
    if st.button("🔍 유사 채널 찾기", type="primary", use_container_width=True):
        st.session_state.similar_channels_loading = True
        st.session_state.similar_channels_data = None

if st.session_state.similar_channels_loading:
    with st.spinner("유사 채널을 찾는 중... (시간이 걸릴 수 있습니다)"):
        try:
            result = similar.find_similar_channels(
                channel_id=selected_channel.youtube_channel_id,
                top_videos_count=top_videos_count,
                related_per_video=related_per_video,
                min_appearances=2
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
                st.metric("수집한 관련 영상", debug_info.get("total_related_videos", 0))

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

        # Display similar channels
        for i, ch in enumerate(similar_channels):
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 2])

                with col1:
                    if ch.get('thumbnail_url'):
                        st.image(ch['thumbnail_url'], width=100)

                with col2:
                    st.markdown(f"### {i+1}. {ch['title']}")
                    if ch.get('handle'):
                        st.markdown(f"**핸들:** @{ch['handle']}")
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
                    if st.button("📊 채널 분석", key=f"analyze_{ch['channel_id']}", use_container_width=True):
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
        } for i, ch in enumerate(similar_channels)]

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
