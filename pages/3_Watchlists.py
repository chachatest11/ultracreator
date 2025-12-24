"""
Watchlists - Channel Grouping and Comparison
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from core import db, metrics

st.set_page_config(page_title="Watchlists", page_icon="📋", layout="wide")

st.title("📋 Watchlists")
st.markdown("채널 그룹 관리 및 비교 분석")

# Initialize session state
if 'refresh_trigger' not in st.session_state:
    st.session_state.refresh_trigger = 0

# Sidebar - Watchlist Management
with st.sidebar:
    st.header("📋 워치리스트 관리")

    # Create new watchlist
    st.subheader("새 워치리스트")
    new_watchlist_name = st.text_input("워치리스트 이름")

    if st.button("생성", use_container_width=True):
        if new_watchlist_name:
            try:
                db.create_watchlist(new_watchlist_name)
                st.success(f"✓ '{new_watchlist_name}' 워치리스트가 생성되었습니다!")
                st.session_state.refresh_trigger += 1
                st.rerun()
            except Exception as e:
                st.error(f"✗ 워치리스트 생성 실패: {e}")
        else:
            st.warning("워치리스트 이름을 입력해주세요.")

    st.markdown("---")

    # Delete watchlist
    watchlists = db.get_all_watchlists()

    if watchlists:
        st.subheader("워치리스트 삭제")
        delete_watchlist = st.selectbox(
            "삭제할 워치리스트",
            [wl.name for wl in watchlists],
            key="delete_watchlist"
        )

        if st.button("삭제", use_container_width=True, type="secondary"):
            delete_wl = next(wl for wl in watchlists if wl.name == delete_watchlist)
            db.delete_watchlist(delete_wl.id)
            st.success(f"✓ '{delete_watchlist}' 워치리스트가 삭제되었습니다!")
            st.session_state.refresh_trigger += 1
            st.rerun()

# Get all watchlists
watchlists = db.get_all_watchlists()

if not watchlists:
    st.info("워치리스트가 없습니다. 사이드바에서 새 워치리스트를 생성해주세요!")
    st.stop()

# Select watchlist
selected_watchlist_name = st.selectbox(
    "워치리스트 선택",
    [wl.name for wl in watchlists]
)

selected_watchlist = next(wl for wl in watchlists if wl.name == selected_watchlist_name)

# Get channels in watchlist
watchlist_channels = db.get_watchlist_channels(selected_watchlist.id)

st.markdown("---")

# Add/Remove channels
st.subheader("🔧 채널 관리")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 채널 추가")

    all_channels = db.get_all_channels()
    watchlist_channel_ids = {ch.id for ch in watchlist_channels}
    available_channels = [ch for ch in all_channels if ch.id not in watchlist_channel_ids]

    if available_channels:
        add_channel = st.selectbox(
            "추가할 채널",
            [ch.title for ch in available_channels],
            key="add_channel"
        )

        if st.button("추가", use_container_width=True):
            add_ch = next(ch for ch in available_channels if ch.title == add_channel)
            db.add_channel_to_watchlist(selected_watchlist.id, add_ch.id)
            st.success(f"✓ '{add_channel}'이(가) 추가되었습니다!")
            st.session_state.refresh_trigger += 1
            st.rerun()
    else:
        st.info("추가할 수 있는 채널이 없습니다.")

with col2:
    st.markdown("#### 채널 제거")

    if watchlist_channels:
        remove_channel = st.selectbox(
            "제거할 채널",
            [ch.title for ch in watchlist_channels],
            key="remove_channel"
        )

        if st.button("제거", use_container_width=True, type="secondary"):
            remove_ch = next(ch for ch in watchlist_channels if ch.title == remove_channel)
            db.remove_channel_from_watchlist(selected_watchlist.id, remove_ch.id)
            st.success(f"✓ '{remove_channel}'이(가) 제거되었습니다!")
            st.session_state.refresh_trigger += 1
            st.rerun()
    else:
        st.info("워치리스트에 채널이 없습니다.")

# Comparison table
st.markdown("---")
st.subheader(f"📊 '{selected_watchlist_name}' 비교표 ({len(watchlist_channels)}개 채널)")

if not watchlist_channels:
    st.info("이 워치리스트에 채널을 추가해주세요.")
    st.stop()

# Build comparison data
comparison_data = []

progress_bar = st.progress(0)
status_text = st.empty()

for i, channel in enumerate(watchlist_channels):
    status_text.text(f"분석 중: {channel.title} ({i+1}/{len(watchlist_channels)})")
    progress_bar.progress((i + 1) / len(watchlist_channels))

    channel_metrics = metrics.get_channel_metrics(channel.id)

    comparison_data.append({
        "순위": i + 1,
        "채널명": channel.title,
        "구독자수": channel_metrics['subscriber_count'],
        "평균 조회수": int(channel_metrics['avg_views_recent_10']),
        "업로드 주기": round(channel_metrics['upload_frequency']['average_days'], 1),
        "조회수 유형": channel_metrics['view_variance']['type'],
        "Shorts 비중": channel_metrics['shorts_metrics']['shorts_ratio'] * 100,
        "7일 성장": channel_metrics['growth_7d']['subscriber_growth'],
        "30일 성장": channel_metrics['growth_30d']['subscriber_growth'],
        "제목 길이": round(channel_metrics['avg_title_length'], 1),
        "Top5 집중도": channel_metrics['top5_concentration'] * 100,
        "가장 많이 올리는 요일": channel_metrics['upload_patterns']['most_common_day'],
        "가장 많이 올리는 시간": channel_metrics['upload_patterns']['most_common_hour']
    })

progress_bar.empty()
status_text.empty()

df = pd.DataFrame(comparison_data)

# Sorting options
col1, col2 = st.columns([3, 1])

with col1:
    sort_by = st.selectbox(
        "정렬 기준",
        ["순위", "구독자수", "평균 조회수", "업로드 주기", "Shorts 비중", "7일 성장", "30일 성장"]
    )

with col2:
    sort_order = st.radio("순서", ["⬇️", "⬆️"], horizontal=True)

ascending = sort_order == "⬆️"
df = df.sort_values(sort_by, ascending=ascending)

# Display table
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "구독자수": st.column_config.NumberColumn(format="%d"),
        "평균 조회수": st.column_config.NumberColumn(format="%d"),
        "Shorts 비중": st.column_config.NumberColumn(format="%.1f%%"),
        "7일 성장": st.column_config.NumberColumn(format="%+d"),
        "30일 성장": st.column_config.NumberColumn(format="%+d"),
        "Top5 집중도": st.column_config.NumberColumn(format="%.1f%%")
    }
)

# Visualizations
st.markdown("---")
st.subheader("📊 시각화")

tab1, tab2, tab3 = st.tabs(["성과 비교", "업로드 패턴", "Shorts 분석"])

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        # Subscriber comparison
        fig = px.bar(
            df,
            x="채널명",
            y="구독자수",
            title="채널별 구독자 수",
            labels={"채널명": "채널", "구독자수": "구독자"}
        )
        fig.update_xaxis(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Average views comparison
        fig = px.bar(
            df,
            x="채널명",
            y="평균 조회수",
            title="채널별 평균 조회수 (최근 10개)",
            labels={"채널명": "채널", "평균 조회수": "평균 조회수"}
        )
        fig.update_xaxis(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # Growth comparison
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df,
            x="채널명",
            y="7일 성장",
            title="7일 구독자 성장",
            labels={"채널명": "채널", "7일 성장": "성장 수"}
        )
        fig.update_xaxis(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df,
            x="채널명",
            y="30일 성장",
            title="30일 구독자 성장",
            labels={"채널명": "채널", "30일 성장": "성장 수"}
        )
        fig.update_xaxis(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("#### 업로드 패턴 분석")

    col1, col2 = st.columns(2)

    with col1:
        # Upload frequency
        fig = px.bar(
            df,
            x="채널명",
            y="업로드 주기",
            title="채널별 업로드 주기 (일)",
            labels={"채널명": "채널", "업로드 주기": "평균 일수"}
        )
        fig.update_xaxis(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        st.caption("숫자가 작을수록 자주 업로드함")

    with col2:
        # Title length
        fig = px.bar(
            df,
            x="채널명",
            y="제목 길이",
            title="채널별 평균 제목 길이",
            labels={"채널명": "채널", "제목 길이": "평균 문자 수"}
        )
        fig.update_xaxis(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # Day and hour patterns
    st.markdown("#### 요일 & 시간대 분포")

    day_summary = df['가장 많이 올리는 요일'].value_counts()
    hour_summary = df['가장 많이 올리는 시간'].value_counts()

    col1, col2 = st.columns(2)

    with col1:
        if not day_summary.empty:
            fig = px.pie(
                values=day_summary.values,
                names=day_summary.index,
                title="채널들이 가장 많이 올리는 요일"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not hour_summary.empty:
            fig = px.bar(
                x=hour_summary.index,
                y=hour_summary.values,
                title="채널들이 가장 많이 올리는 시간대 (KST)",
                labels={"x": "시간 (시)", "y": "채널 수"}
            )
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("#### Shorts 분석")

    col1, col2 = st.columns(2)

    with col1:
        # Shorts ratio
        fig = px.bar(
            df,
            x="채널명",
            y="Shorts 비중",
            title="채널별 Shorts 비중 (%)",
            labels={"채널명": "채널", "Shorts 비중": "비중 (%)"}
        )
        fig.update_xaxis(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Top5 concentration
        fig = px.bar(
            df,
            x="채널명",
            y="Top5 집중도",
            title="Top5 조회수 집중도 (%)",
            labels={"채널명": "채널", "Top5 집중도": "집중도 (%)"}
        )
        fig.update_xaxis(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        st.caption("높을수록 특정 영상에 조회수가 집중됨")

    # Scatter plot: Shorts ratio vs Average views
    st.markdown("#### Shorts 비중 vs 평균 조회수")

    fig = px.scatter(
        df,
        x="Shorts 비중",
        y="평균 조회수",
        text="채널명",
        title="Shorts 비중과 평균 조회수의 관계",
        labels={"Shorts 비중": "Shorts 비중 (%)", "평균 조회수": "평균 조회수"}
    )
    fig.update_traces(textposition='top center')
    st.plotly_chart(fig, use_container_width=True)

# Summary insights
st.markdown("---")
st.subheader("💡 인사이트")

col1, col2, col3 = st.columns(3)

with col1:
    avg_shorts = df['Shorts 비중'].mean()
    st.metric("평균 Shorts 비중", f"{avg_shorts:.1f}%")

with col2:
    avg_upload_freq = df['업로드 주기'].mean()
    st.metric("평균 업로드 주기", f"{avg_upload_freq:.1f}일")

with col3:
    avg_title_len = df['제목 길이'].mean()
    st.metric("평균 제목 길이", f"{avg_title_len:.1f}자")

# Top performers
st.markdown("#### 🏆 성과 상위 채널")

col1, col2, col3 = st.columns(3)

with col1:
    top_subs = df.nlargest(3, '구독자수')[['채널명', '구독자수']]
    st.markdown("**구독자 TOP 3**")
    for idx, row in top_subs.iterrows():
        st.markdown(f"- {row['채널명']}: {row['구독자수']:,}")

with col2:
    top_views = df.nlargest(3, '평균 조회수')[['채널명', '평균 조회수']]
    st.markdown("**평균 조회수 TOP 3**")
    for idx, row in top_views.iterrows():
        st.markdown(f"- {row['채널명']}: {row['평균 조회수']:,}")

with col3:
    top_growth = df.nlargest(3, '30일 성장')[['채널명', '30일 성장']]
    st.markdown("**30일 성장 TOP 3**")
    for idx, row in top_growth.iterrows():
        st.markdown(f"- {row['채널명']}: +{row['30일 성장']:,}")

# Footer
st.markdown("---")
st.caption("💡 팁: 워치리스트를 활용하여 경쟁 채널을 그룹화하고 비교 분석하세요!")
