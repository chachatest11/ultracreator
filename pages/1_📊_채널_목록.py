"""
Dashboard - Channel List and Management
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from core import db, jobs, metrics

st.set_page_config(page_title="📊 채널 목록", page_icon="📊", layout="wide")

st.title("📊 채널 목록")
st.markdown("관심 채널 관리 및 주요 지표 모니터링")

# Initialize session state
if 'refresh_trigger' not in st.session_state:
    st.session_state.refresh_trigger = 0
if 'confirm_delete_channel_id' not in st.session_state:
    st.session_state.confirm_delete_channel_id = None
if 'selected_channel_id' not in st.session_state:
    st.session_state.selected_channel_id = None

# Sidebar - Add Channel
with st.sidebar:
    st.header("➕ 채널 추가")

    # Get all groups for selection
    all_groups_sidebar = db.get_all_watchlists()

    # Use form to enable Enter key submission
    with st.form(key="add_channel_form"):
        channel_input = st.text_area(
            "채널 ID, 핸들, 또는 URL (여러 개 입력 시 줄바꿈)",
            placeholder="UC..., @username, https://youtube.com/@...\n한 줄에 하나씩 입력",
            height=100
        )

        # Group selection
        if all_groups_sidebar:
            selected_groups = st.multiselect(
                "그룹에 추가 (선택사항)",
                [wl.name for wl in all_groups_sidebar],
                help="채널을 추가할 그룹을 선택하세요. 여러 개 선택 가능합니다."
            )
        else:
            selected_groups = []
            st.info("💡 그룹이 없습니다. '⭐ 그룹 관리' 페이지에서 그룹을 먼저 생성하세요.")

        submit_button = st.form_submit_button("채널 추가", type="primary", use_container_width=True)

    if submit_button:
        if channel_input:
            # Split by newlines and filter out empty lines
            channel_inputs = [line.strip() for line in channel_input.split('\n') if line.strip()]

            if len(channel_inputs) == 1:
                # Single channel - simple process
                with st.spinner("채널 데이터를 수집하는 중..."):
                    progress_placeholder = st.empty()

                    def show_progress(msg):
                        progress_placeholder.info(msg)

                    result = jobs.fetch_channel_data(
                        channel_inputs[0],
                        force_refresh=False,
                        progress_callback=show_progress
                    )

                    if result:
                        # Add to selected groups
                        if selected_groups:
                            channel = result  # Result is the channel object
                            for group_name in selected_groups:
                                group_wl = next(wl for wl in all_groups_sidebar if wl.name == group_name)
                                db.add_channel_to_watchlist(group_wl.id, channel.id)
                            st.success(f"✓ 채널이 추가되고 {len(selected_groups)}개 그룹에 할당되었습니다!")
                        else:
                            st.success("✓ 채널이 추가되었습니다!")
                        st.session_state.refresh_trigger += 1
                        st.rerun()
                    else:
                        st.error("✗ 채널 추가에 실패했습니다. 입력값을 확인해주세요.")
            else:
                # Multiple channels - batch process
                progress_placeholder = st.empty()
                status_placeholder = st.empty()

                success_count = 0
                failed_count = 0
                failed_channels = []
                added_channels = []  # Track successfully added channels

                for idx, single_input in enumerate(channel_inputs, 1):
                    progress_placeholder.progress(idx / len(channel_inputs),
                        text=f"진행 중: {idx}/{len(channel_inputs)} - {single_input[:30]}...")

                    try:
                        result = jobs.fetch_channel_data(
                            single_input,
                            force_refresh=False,
                            progress_callback=lambda msg: None
                        )

                        if result:
                            success_count += 1
                            added_channels.append(result)  # Save successfully added channel
                            status_placeholder.success(
                                f"✓ {success_count}개 성공, {failed_count}개 실패"
                            )
                        else:
                            failed_count += 1
                            failed_channels.append(single_input)
                            status_placeholder.warning(
                                f"✓ {success_count}개 성공, {failed_count}개 실패"
                            )
                    except Exception as e:
                        failed_count += 1
                        failed_channels.append(f"{single_input} (오류: {str(e)})")
                        status_placeholder.warning(
                            f"✓ {success_count}개 성공, {failed_count}개 실패"
                        )

                progress_placeholder.empty()

                # Add all successful channels to selected groups
                if selected_groups and added_channels:
                    for channel in added_channels:
                        for group_name in selected_groups:
                            group_wl = next(wl for wl in all_groups_sidebar if wl.name == group_name)
                            db.add_channel_to_watchlist(group_wl.id, channel.id)

                # Final result
                if selected_groups and success_count > 0:
                    st.success(f"🎉 완료! {success_count}개 채널 추가 성공 ({len(selected_groups)}개 그룹에 할당), {failed_count}개 실패")
                else:
                    st.success(f"🎉 완료! {success_count}개 채널 추가 성공, {failed_count}개 실패")

                if failed_channels:
                    with st.expander(f"❌ 실패한 채널 ({failed_count}개)"):
                        for failed in failed_channels:
                            st.text(failed)

                st.session_state.refresh_trigger += 1
                st.rerun()
        else:
            st.warning("채널 정보를 입력해주세요.")

    st.markdown("---")

    st.header("📂 CSV 일괄 추가")
    st.caption("채널 핸들/ID를 한 줄에 하나씩 입력한 CSV 파일")

    uploaded_file = st.file_uploader(
        "CSV 파일 업로드",
        type=['csv', 'txt'],
        help="형식: 각 줄에 @handle 또는 채널ID"
    )

    if uploaded_file is not None:
        if st.button("📥 CSV에서 채널 추가", type="primary", width="stretch"):
            try:
                # Read CSV file
                content = uploaded_file.getvalue().decode('utf-8')
                lines = [line.strip() for line in content.split('\n') if line.strip()]

                # Remove header if exists (contains 'channel', 'handle', 'id', etc.)
                if lines and any(keyword in lines[0].lower() for keyword in ['channel', 'handle', 'id', 'url']):
                    lines = lines[1:]

                if not lines:
                    st.warning("CSV 파일이 비어있습니다.")
                else:
                    progress_placeholder = st.empty()
                    status_placeholder = st.empty()

                    success_count = 0
                    failed_count = 0
                    failed_channels = []

                    for idx, channel_input in enumerate(lines, 1):
                        progress_placeholder.progress(idx / len(lines),
                            text=f"진행 중: {idx}/{len(lines)} - {channel_input[:30]}...")

                        try:
                            result = jobs.fetch_channel_data(
                                channel_input,
                                force_refresh=False,
                                progress_callback=lambda msg: None
                            )

                            if result:
                                success_count += 1
                                status_placeholder.success(
                                    f"✓ {success_count}개 성공, {failed_count}개 실패"
                                )
                            else:
                                failed_count += 1
                                failed_channels.append(channel_input)
                                status_placeholder.warning(
                                    f"✓ {success_count}개 성공, {failed_count}개 실패"
                                )
                        except Exception as e:
                            failed_count += 1
                            failed_channels.append(f"{channel_input} (오류: {str(e)})")
                            status_placeholder.warning(
                                f"✓ {success_count}개 성공, {failed_count}개 실패"
                            )

                    progress_placeholder.empty()

                    # Final result
                    st.success(f"🎉 완료! {success_count}개 채널 추가 성공, {failed_count}개 실패")

                    if failed_channels:
                        with st.expander(f"❌ 실패한 채널 ({failed_count}개)"):
                            for failed in failed_channels:
                                st.text(failed)

                    st.session_state.refresh_trigger += 1
                    st.rerun()

            except Exception as e:
                st.error(f"CSV 파일 처리 중 오류: {str(e)}")

    st.markdown("---")

    st.header("🔄 전체 갱신")
    if st.button("모든 채널 갱신", width="stretch"):
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

col1, col2, col3, col4 = st.columns(4)

# Get all groups for filtering
all_groups = db.get_all_watchlists()
group_options = ["전체"] + [wl.name for wl in all_groups]

with col1:
    selected_group = st.selectbox(
        "🏷️ 그룹",
        group_options,
        help="그룹별로 채널을 필터링합니다"
    )

with col2:
    filter_preset = st.selectbox(
        "프리셋",
        ["없음", "Shorts 중심", "해외 양산형"]
    )

with col3:
    sort_by = st.selectbox(
        "정렬 기준",
        ["최근 추가순", "구독자수", "평균 조회수", "업로드 빈도", "Shorts 비중"]
    )

with col4:
    sort_order = st.radio("정렬 순서", ["내림차순", "오름차순"], horizontal=True)

# Get filtered channels by group
if selected_group != "전체":
    # Get group ID
    selected_watchlist = next(wl for wl in all_groups if wl.name == selected_group)
    # Get channels in this group
    group_channels = db.get_watchlist_channels(selected_watchlist.id)
    group_channel_ids = {ch.id for ch in group_channels}
    # Filter channels
    channels = [ch for ch in channels if ch.id in group_channel_ids]

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

    # Get channel groups
    channel_groups = []
    for wl in all_groups:
        wl_channels = db.get_watchlist_channels(wl.id)
        if any(wl_ch.id == channel.id for wl_ch in wl_channels):
            channel_groups.append(wl.name)

    groups_display = ", ".join(channel_groups) if channel_groups else "-"

    # Create YouTube URL
    handle_clean = channel.handle.lstrip('@') if channel.handle else ''
    if handle_clean:
        youtube_url = f"https://www.youtube.com/@{handle_clean}"
    else:
        youtube_url = f"https://www.youtube.com/channel/{channel.youtube_channel_id}"

    channel_data.append({
        "ID": channel.id,
        "채널명": channel.title,
        "그룹": groups_display,
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

# Display table (read-only, no selection)
st.dataframe(
    df,
    width="stretch",
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

# Quick delete - Channel list with delete buttons
with st.expander("🗑️ 채널 삭제", expanded=False):
    st.caption("채널 옆의 삭제 버튼을 클릭하여 즉시 삭제할 수 있습니다.")

    # Display channels in a compact grid
    for idx in range(0, len(df), 2):  # 2 columns per row
        cols = st.columns([5, 1, 5, 1])

        # First channel in row
        with cols[0]:
            channel_name = df.iloc[idx]['채널명']
            st.markdown(f"**{channel_name}**")
        with cols[1]:
            channel_id = df.iloc[idx]['ID']
            if st.button("🗑️", key=f"del_{channel_id}", help=f"'{channel_name}' 삭제"):
                try:
                    result = db.delete_channel(channel_id)
                    if result == "already_deleted":
                        st.warning(f"⚠️ '{channel_name}'은(는) 이미 삭제되었습니다. 새로고침합니다.")
                    else:
                        st.success(f"✓ '{channel_name}' 삭제됨")
                    st.session_state.refresh_trigger += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"✗ 삭제 실패: {str(e)}")

        # Second channel in row (if exists)
        if idx + 1 < len(df):
            with cols[2]:
                channel_name = df.iloc[idx + 1]['채널명']
                st.markdown(f"**{channel_name}**")
            with cols[3]:
                channel_id = df.iloc[idx + 1]['ID']
                if st.button("🗑️", key=f"del_{channel_id}", help=f"'{channel_name}' 삭제"):
                    try:
                        result = db.delete_channel(channel_id)
                        if result == "already_deleted":
                            st.warning(f"⚠️ '{channel_name}'은(는) 이미 삭제되었습니다. 새로고침합니다.")
                        else:
                            st.success(f"✓ '{channel_name}' 삭제됨")
                        st.session_state.refresh_trigger += 1
                        st.rerun()
                    except Exception as e:
                        st.error(f"✗ 삭제 실패: {str(e)}")

st.markdown("---")

# Channel actions
st.subheader("🔧 채널 작업")

# Only show channel actions if there are channels
if len(df) > 0:
    # Create channel name to ID mapping for reliable selection
    channel_name_to_id = dict(zip(df['채널명'], df['ID']))

    # Channel selector
    selected_channel_name = st.selectbox(
        "작업할 채널 선택",
        list(channel_name_to_id.keys()),
        key="channel_action_select"
    )

    # Get selected channel ID from mapping
    selected_channel_id = channel_name_to_id[selected_channel_name]

    # Update session state
    st.session_state.selected_channel_id = selected_channel_id

    # Get channel object directly
    try:
        selected_channel = db.get_channel_by_id(int(selected_channel_id))
    except Exception as e:
        st.error(f"⚠️ 채널 조회 중 오류 발생: {e}")
        st.error(f"디버그 정보 - Channel ID: {selected_channel_id} (타입: {type(selected_channel_id)})")
        selected_channel = None

    if selected_channel:
        selected_channel_name = selected_channel.title

        # Display selected channel details
        st.markdown("---")
        st.markdown(f"### 📊 선택한 채널: **{selected_channel_name}**")

        # Get latest snapshot for channel data
        latest_snapshot = db.get_latest_channel_snapshot(selected_channel_id)

        if latest_snapshot:
            subscriber_count = latest_snapshot.subscriber_count
            view_count = latest_snapshot.view_count
        else:
            # No snapshot available - need to fetch data
            subscriber_count = 0
            view_count = 0

        views_48h = metrics.calculate_views_48h(selected_channel_id)

        col_info1, col_info2, col_info3 = st.columns(3)

        with col_info1:
            st.metric(
                "구독자",
                f"{subscriber_count:,}"
            )

        with col_info2:
            st.metric(
                "총 조회수",
                f"{view_count:,}"
            )

        with col_info3:
            st.metric(
                "최근 48시간 조회수",
                f"{views_48h:,}"
            )

        # If no snapshot, show warning and offer to fetch
        if not latest_snapshot:
            st.warning("⚠️ 채널 데이터가 없습니다. 데이터를 가져오려면 '📡 데이터 업데이트'를 실행하세요.")
            if st.button("🔄 지금 데이터 가져오기", key="fetch_selected_channel"):
                with st.spinner(f"{selected_channel_name} 데이터를 가져오는 중..."):
                    try:
                        jobs.fetch_channel_data(selected_channel_id)
                        st.success("✓ 데이터를 가져왔습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"✗ 데이터 가져오기 실패: {e}")

        st.markdown("---")

        # Group management for selected channel
        st.subheader("🏷️ 그룹 관리")

        # Get current groups for this channel
        current_groups = []
        for wl in all_groups:
            wl_channels = db.get_watchlist_channels(wl.id)
            if any(wl_ch.id == selected_channel_id for wl_ch in wl_channels):
                current_groups.append(wl.name)

        if current_groups:
            st.success(f"**현재 그룹:** {', '.join(current_groups)}")
        else:
            st.info("이 채널은 아직 그룹에 속해있지 않습니다.")

        col_group1, col_group2 = st.columns(2)

        with col_group1:
            st.markdown("#### 그룹에 추가")
            if all_groups:
                # Get groups that don't have this channel
                available_groups = [wl.name for wl in all_groups if wl.name not in current_groups]

                if available_groups:
                    add_to_groups = st.multiselect(
                        "추가할 그룹 선택",
                        available_groups,
                        key="add_to_groups"
                    )

                    if st.button("그룹에 추가", width="stretch", type="primary"):
                        if add_to_groups:
                            for group_name in add_to_groups:
                                group_wl = next(wl for wl in all_groups if wl.name == group_name)
                                db.add_channel_to_watchlist(group_wl.id, selected_channel_id)
                            st.success(f"✓ {len(add_to_groups)}개 그룹에 추가됨!")
                            st.session_state.refresh_trigger += 1
                            st.rerun()
                        else:
                            st.warning("그룹을 선택하세요.")
                else:
                    st.info("모든 그룹에 이미 추가되어 있습니다.")
            else:
                st.info("먼저 그룹을 생성하세요.")

        with col_group2:
            st.markdown("#### 그룹에서 제거")
            if current_groups:
                remove_from_groups = st.multiselect(
                    "제거할 그룹 선택",
                    current_groups,
                    key="remove_from_groups"
                )

                if st.button("그룹에서 제거", width="stretch", type="secondary"):
                    if remove_from_groups:
                        for group_name in remove_from_groups:
                            group_wl = next(wl for wl in all_groups if wl.name == group_name)
                            db.remove_channel_from_watchlist(group_wl.id, selected_channel_id)
                        st.success(f"✓ {len(remove_from_groups)}개 그룹에서 제거됨!")
                        st.session_state.refresh_trigger += 1
                        st.rerun()
                    else:
                        st.warning("그룹을 선택하세요.")
            else:
                st.info("제거할 그룹이 없습니다.")

        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📊 상세 보기", width="stretch"):
                # Store selected channel in session state
                st.session_state.selected_channel_id = selected_channel_id
                st.switch_page("pages/2_📈_상세_분석.py")

        with col2:
            if st.button("🔄 채널 갱신", width="stretch"):
                with st.spinner("채널을 갱신하는 중..."):
                    progress_placeholder = st.empty()

                    def show_progress(msg):
                        progress_placeholder.info(msg)

                    # Get the channel to verify it exists
                    channel = db.get_channel_by_id(selected_channel_id)
                    if not channel:
                        st.error("✗ 선택한 채널을 찾을 수 없습니다. 페이지를 새로고침하세요.")
                    else:
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
                    if st.button("✓ 삭제", key="confirm_delete", width="stretch", type="primary"):
                        try:
                            result = db.delete_channel(selected_channel_id)
                            st.session_state.confirm_delete_channel_id = None
                            if result == "already_deleted":
                                st.warning(f"⚠️ '{selected_channel_name}'은(는) 이미 삭제되었습니다. 새로고침합니다.")
                            else:
                                st.success("✓ 채널이 삭제되었습니다!")
                            st.session_state.refresh_trigger += 1
                            st.rerun()
                        except Exception as e:
                            st.error(f"✗ 삭제 실패: {str(e)}")
                            st.session_state.confirm_delete_channel_id = None
                with col_no:
                    if st.button("✗ 취소", key="cancel_delete", width="stretch"):
                        st.session_state.confirm_delete_channel_id = None
                        st.rerun()
            else:
                if st.button("🗑️ 채널 삭제", width="stretch", type="secondary"):
                    st.session_state.confirm_delete_channel_id = selected_channel_id
                    st.rerun()
    else:
        st.error("⚠️ 선택한 채널을 찾을 수 없습니다. 페이지를 새로고침하세요.")
else:
    st.info("📌 채널을 먼저 추가해주세요")

# Footer
st.markdown("---")
st.caption("💡 팁: 채널명을 클릭하여 상세 페이지로 이동하거나, 위의 버튼으로 작업을 수행하세요.")
