"""
Dashboard - Channel List and Management
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from core import db, jobs, metrics

st.set_page_config(page_title="Dashboard", page_icon="📈", layout="wide")

st.title("📈 Dashboard")
st.markdown("관심 채널 관리 및 주요 지표 모니터링")

# Initialize session state
if 'refresh_trigger' not in st.session_state:
    st.session_state.refresh_trigger = 0
if 'confirm_delete_channel_id' not in st.session_state:
    st.session_state.confirm_delete_channel_id = None

# Sidebar - Add Channel
with st.sidebar:
    st.header("➕ 채널 추가")

    channel_input = st.text_input(
        "채널 ID, 핸들, 또는 URL",
        placeholder="UC..., @username, https://youtube.com/@..."
    )

    if st.button("채널 추가", type="primary", use_container_width=True):
        if channel_input:
            with st.spinner("채널 데이터를 수집하는 중..."):
                progress_placeholder = st.empty()

                def show_progress(msg):
                    progress_placeholder.info(msg)

                result = jobs.fetch_channel_data(
                    channel_input,
                    force_refresh=False,
                    progress_callback=show_progress
                )

                if result:
                    st.success("✓ 채널이 추가되었습니다!")
                    st.session_state.refresh_trigger += 1
                    st.rerun()
                else:
                    st.error("✗ 채널 추가에 실패했습니다. 입력값을 확인해주세요.")
        else:
            st.warning("채널 정보를 입력해주세요.")

    st.markdown("---")

    st.header("🔄 전체 갱신")
    if st.button("모든 채널 갱신", use_container_width=True):
        with st.spinner("모든 채널을 갱신하는 중..."):
            progress_placeholder = st.empty()

            def show_progress(msg):
                progress_placeholder.info(msg)

            results = jobs.refresh_all_channels(progress_callback=show_progress)

            st.success(
                f"✓ 갱신 완료: {results['success']}개 성공, {results['failed']}개 실패"
            )
            st.session_state.refresh_trigger += 1
            st.rerun()

# Get all channels
channels = db.get_all_channels()

if not channels:
    st.info("아직 등록된 채널이 없습니다. 사이드바에서 채널을 추가해보세요!")
    st.stop()

# Filter options
st.subheader("🎛️ 필터 & 정렬")

col1, col2, col3 = st.columns(3)

with col1:
    filter_preset = st.selectbox(
        "프리셋",
        ["없음", "Shorts 중심", "해외 양산형"]
    )

with col2:
    sort_by = st.selectbox(
        "정렬 기준",
        ["최근 추가순", "구독자수", "평균 조회수", "업로드 빈도", "Shorts 비중"]
    )

with col3:
    sort_order = st.radio("정렬 순서", ["내림차순", "오름차순"], horizontal=True)

# Build channel data
channel_data = []

progress_bar = st.progress(0)
status_text = st.empty()

for i, channel in enumerate(channels):
    status_text.text(f"분석 중: {channel.title} ({i+1}/{len(channels)})")
    progress_bar.progress((i + 1) / len(channels))

    channel_metrics = metrics.get_channel_metrics(channel.id)

    # Apply filters
    shorts_ratio = channel_metrics['shorts_metrics']['shorts_ratio']
    upload_freq = channel_metrics['upload_frequency']['average_days']
    view_variance = channel_metrics['view_variance']['cv']

    # Filter preset logic
    if filter_preset == "Shorts 중심":
        if shorts_ratio < 0.5:  # Less than 50% shorts
            continue
    elif filter_preset == "해외 양산형":
        if upload_freq > 7 or view_variance < 0.3:  # Not frequent enough or too stable
            continue

    # Create YouTube URL
    handle_clean = channel.handle.lstrip('@') if channel.handle else ''
    if handle_clean:
        youtube_url = f"https://www.youtube.com/@{handle_clean}"
    else:
        youtube_url = f"https://www.youtube.com/channel/{channel.youtube_channel_id}"

    channel_data.append({
        "ID": channel.id,
        "채널명": channel.title,
        "YouTube": youtube_url,
        "핸들": channel.handle,
        "구독자수": channel_metrics['subscriber_count'],
        "평균 조회수 (10개)": int(channel_metrics['avg_views_recent_10']),
        "업로드 주기 (일)": round(upload_freq, 1),
        "조회수 분산 유형": channel_metrics['view_variance']['type'],
        "Shorts 비중": f"{shorts_ratio * 100:.1f}%",
        "7일 성장": channel_metrics['growth_7d']['subscriber_growth'],
        "30일 성장": channel_metrics['growth_30d']['subscriber_growth'],
        "제목 길이": round(channel_metrics['avg_title_length'], 1),
        "Top5 집중도": f"{channel_metrics['top5_concentration'] * 100:.1f}%",
        "마지막 갱신": channel.last_fetched_at.strftime("%Y-%m-%d %H:%M") if channel.last_fetched_at else "N/A"
    })

progress_bar.empty()
status_text.empty()

if not channel_data:
    st.warning("필터 조건에 맞는 채널이 없습니다.")
    st.stop()

# Create DataFrame
df = pd.DataFrame(channel_data)

# Sort
sort_key_map = {
    "최근 추가순": "ID",
    "구독자수": "구독자수",
    "평균 조회수": "평균 조회수 (10개)",
    "업로드 빈도": "업로드 주기 (일)",
    "Shorts 비중": "Shorts 비중"
}

sort_key = sort_key_map[sort_by]
ascending = sort_order == "오름차순"

# Handle special sorting for percentage strings
if sort_key == "Shorts 비중":
    df['_shorts_sort'] = df['Shorts 비중'].str.rstrip('%').astype(float)
    df = df.sort_values('_shorts_sort', ascending=ascending)
    df = df.drop(columns=['_shorts_sort'])
else:
    df = df.sort_values(sort_key, ascending=ascending)

# Display summary stats
st.subheader(f"📊 채널 목록 ({len(df)}개)")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("총 구독자", f"{df['구독자수'].sum():,}")

with col2:
    st.metric("평균 조회수", f"{int(df['평균 조회수 (10개)'].mean()):,}")

with col3:
    shorts_avg = df['Shorts 비중'].str.rstrip('%').astype(float).mean()
    st.metric("평균 Shorts 비중", f"{shorts_avg:.1f}%")

with col4:
    st.metric("평균 업로드 주기", f"{df['업로드 주기 (일)'].mean():.1f}일")

# Display table
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "ID": None,  # Hide ID column
        "YouTube": st.column_config.LinkColumn(
            "YouTube 링크",
            display_text="🔗 채널 보기"
        ),
        "구독자수": st.column_config.NumberColumn(format="%d"),
        "평균 조회수 (10개)": st.column_config.NumberColumn(format="%d"),
        "7일 성장": st.column_config.NumberColumn(format="%+d"),
        "30일 성장": st.column_config.NumberColumn(format="%+d")
    }
)

# Channel actions
st.subheader("🔧 채널 작업")

selected_channel_name = st.selectbox(
    "채널 선택",
    df['채널명'].tolist()
)

selected_channel_id = df[df['채널명'] == selected_channel_name]['ID'].iloc[0]

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 상세 보기", use_container_width=True):
        st.switch_page("pages/2_Channel_Detail.py")
        # Store selected channel in session state
        st.session_state.selected_channel_id = selected_channel_id

with col2:
    if st.button("🔄 채널 갱신", use_container_width=True):
        with st.spinner("채널을 갱신하는 중..."):
            progress_placeholder = st.empty()

            def show_progress(msg):
                progress_placeholder.info(msg)

            success = jobs.refresh_channel_data(
                selected_channel_id,
                progress_callback=show_progress
            )

            if success:
                st.success("✓ 채널이 갱신되었습니다!")
                st.session_state.refresh_trigger += 1
                st.rerun()
            else:
                st.error("✗ 채널 갱신에 실패했습니다.")

with col3:
    # Check if we're in delete confirmation mode for this channel
    if st.session_state.confirm_delete_channel_id == selected_channel_id:
        st.warning(f"⚠️ '{selected_channel_name}' 채널을 삭제하시겠습니까?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✓ 삭제", key="confirm_delete", use_container_width=True, type="primary"):
                db.delete_channel(selected_channel_id)
                st.session_state.confirm_delete_channel_id = None
                st.success("✓ 채널이 삭제되었습니다!")
                st.session_state.refresh_trigger += 1
                st.rerun()
        with col_no:
            if st.button("✗ 취소", key="cancel_delete", use_container_width=True):
                st.session_state.confirm_delete_channel_id = None
                st.rerun()
    else:
        if st.button("🗑️ 채널 삭제", use_container_width=True, type="secondary"):
            st.session_state.confirm_delete_channel_id = selected_channel_id
            st.rerun()

# Footer
st.markdown("---")
st.caption("💡 팁: 채널명을 클릭하여 상세 페이지로 이동하거나, 위의 버튼으로 작업을 수행하세요.")
