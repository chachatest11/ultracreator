"""
Channel Detail - Detailed Channel Analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from core import db, metrics

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

# Footer
st.markdown("---")
st.caption("💡 팁: 이 페이지에서 채널의 모든 세부 정보를 확인할 수 있습니다.")
