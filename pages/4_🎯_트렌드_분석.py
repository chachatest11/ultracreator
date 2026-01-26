"""
Niche Explorer - Keyword-based Niche Discovery
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
from core.niche import NicheExplorer, get_niche_results
from core import db, jobs

st.set_page_config(page_title="🎯 트렌드 분석", page_icon="🎯", layout="wide")


# Video player dialog
@st.dialog("🎬 영상 재생", width="large")
def show_video_player(video_id, video_title):
    """Display video player in a dialog"""
    st.markdown(f"**{video_title}**")

    # YouTube video player
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    st.video(video_url)

    if st.button("❌ 닫기", width="stretch"):
        st.rerun()


st.title("🎯 트렌드 분석")
st.markdown("키워드 기반 니치 탐색 및 클러스터 분석")

# Initialize session state
if 'niche_run_id' not in st.session_state:
    st.session_state.niche_run_id = None
if 'all_videos' not in st.session_state:
    st.session_state.all_videos = None

# Input section
st.subheader("🔍 탐색 설정")

# Use form to enable Enter key submission
with st.form(key="niche_search_form"):
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

    with col1:
        keyword = st.text_input(
            "키워드",
            placeholder="예: cute animals, cooking shorts, travel tips",
            help="영어 키워드 권장 (YouTube 검색은 영어가 더 많은 결과를 반환)"
        )

    with col2:
        max_videos = st.number_input(
            "최대 영상 수",
            min_value=50,
            max_value=500,
            value=200,
            step=50,
            help="수집할 영상 개수 (많을수록 정확하지만 느림)"
        )

    with col3:
        n_clusters = st.number_input(
            "클러스터 수",
            min_value=3,
            max_value=15,
            value=8,
            step=1,
            help="그룹화할 클러스터 개수"
        )

    with col4:
        use_cache = st.checkbox(
            "캐시 사용",
            value=True,
            help="24시간 내 동일 검색 결과 재사용"
        )

    # Search button (form submit button)
    submit_button = st.form_submit_button("🚀 탐색 시작", type="primary", use_container_width=True)

# Handle form submission
if submit_button:
    if not keyword:
        st.error("키워드를 입력해주세요.")
    else:
        with st.spinner(f"'{keyword}' 키워드로 니치를 탐색하는 중..."):
            try:
                explorer = NicheExplorer()

                # Progress updates
                progress_placeholder = st.empty()
                progress_bar = st.progress(0)

                progress_placeholder.info("📥 YouTube에서 영상 검색 중...")
                progress_bar.progress(0.2)

                progress_placeholder.info("📊 영상 상세 정보 수집 중...")
                progress_bar.progress(0.4)

                progress_placeholder.info("🤖 AI 임베딩 생성 중...")
                progress_bar.progress(0.6)

                progress_placeholder.info("🔬 클러스터링 분석 중...")
                progress_bar.progress(0.8)

                result = explorer.explore(
                    keyword=keyword,
                    max_videos=max_videos,
                    n_clusters=n_clusters,
                    use_cache=use_cache
                )

                progress_bar.progress(1.0)
                progress_placeholder.empty()
                progress_bar.empty()

                if result:
                    st.session_state.niche_run_id = result['niche_run_id']
                    st.session_state.all_videos = result.get('all_videos')

                    if result.get('from_cache'):
                        st.info("✓ 캐시된 결과를 불러왔습니다. (전체 영상 목록은 캐시되지 않음)")
                    else:
                        st.success(f"✓ 탐색 완료! {n_clusters}개의 클러스터를 발견했습니다.")
                    st.rerun()
                else:
                    st.error("탐색에 실패했습니다. 다른 키워드로 시도해보세요.")

            except Exception as e:
                st.error(f"오류 발생: {e}")

# Display results
if st.session_state.niche_run_id:
    st.markdown("---")
    st.subheader("📊 탐색 결과")

    try:
        results = get_niche_results(st.session_state.niche_run_id)
        clusters = results['clusters']

        # Build DataFrame
        cluster_data = []

        for cluster in clusters:
            cluster_data.append({
                "클러스터": f"#{cluster['cluster_index']}",
                "라벨": cluster['label'],
                "영상 수": cluster['video_count'],
                "중앙 조회수": cluster['median_views'],
                "평균 조회수": cluster['avg_views'],
                "고유 채널 수": cluster['unique_channels'],
                "Top10 집중도": f"{cluster['top10_concentration'] * 100:.1f}%",
                "Shorts 비중": f"{cluster['shorts_ratio'] * 100:.1f}%",
                "종합 점수": round(cluster['final_score'], 2)
            })

        df = pd.DataFrame(cluster_data)

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("총 클러스터", len(clusters))

        with col2:
            total_videos = sum(c['video_count'] for c in clusters)
            st.metric("분석된 영상", total_videos)

        with col3:
            avg_channels = sum(c['unique_channels'] for c in clusters) / len(clusters)
            st.metric("평균 고유 채널", f"{avg_channels:.0f}")

        with col4:
            avg_shorts = sum(c['shorts_ratio'] for c in clusters) / len(clusters)
            st.metric("평균 Shorts 비중", f"{avg_shorts * 100:.1f}%")

        # Display table
        st.markdown("#### 클러스터 요약")

        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            column_config={
                "중앙 조회수": st.column_config.NumberColumn(format="%d"),
                "평균 조회수": st.column_config.NumberColumn(format="%d"),
                "종합 점수": st.column_config.NumberColumn(format="%.2f")
            }
        )

        st.caption("""
        **종합 점수 공식:** 성과 - 0.7×경쟁 - 0.5×집중도
        - 높을수록 진입하기 좋은 니치
        - 성과 = log(중앙 조회수 + 1)
        - 경쟁 = log(고유 채널 수 + 1)
        - 집중도 = Top10 조회수 비중 (높을수록 소수에 집중)
        """)

        # Visualizations
        st.markdown("---")
        st.subheader("📈 시각화")

        tab1, tab2, tab3 = st.tabs(["점수 분석", "성과 vs 경쟁", "Shorts 분석"])

        with tab1:
            # Final score comparison
            fig = px.bar(
                df,
                x="클러스터",
                y="종합 점수",
                color="종합 점수",
                title="클러스터별 종합 점수",
                labels={"종합 점수": "점수"},
                color_continuous_scale="RdYlGn"
            )
            st.plotly_chart(fig, width="stretch")

            st.markdown("#### 점수 구성 요소")

            # Extract score components
            score_components = []
            for cluster in clusters:
                score_components.append({
                    "클러스터": f"#{cluster['cluster_index']}",
                    "성과 점수": cluster['performance_score'],
                    "경쟁 점수": cluster['competition_score'],
                    "집중도 점수": cluster['concentration_score']
                })

            score_df = pd.DataFrame(score_components)

            fig = px.bar(
                score_df.melt(id_vars=['클러스터'], var_name='구성요소', value_name='점수'),
                x="클러스터",
                y="점수",
                color="구성요소",
                barmode="group",
                title="클러스터별 점수 구성 요소"
            )
            st.plotly_chart(fig, width="stretch")

        with tab2:
            # Performance vs Competition scatter
            scatter_data = []
            for cluster in clusters:
                scatter_data.append({
                    "클러스터": cluster['label'][:30],  # Truncate long labels
                    "중앙 조회수": cluster['median_views'],
                    "고유 채널 수": cluster['unique_channels'],
                    "종합 점수": cluster['final_score']
                })

            scatter_df = pd.DataFrame(scatter_data)

            fig = px.scatter(
                scatter_df,
                x="고유 채널 수",
                y="중앙 조회수",
                size="종합 점수",
                color="종합 점수",
                text="클러스터",
                title="성과 vs 경쟁 분포",
                labels={"고유 채널 수": "경쟁 (고유 채널 수)", "중앙 조회수": "성과 (중앙 조회수)"},
                color_continuous_scale="RdYlGn"
            )
            fig.update_traces(textposition='top center')
            st.plotly_chart(fig, width="stretch")

            st.caption("오른쪽 위: 높은 성과 + 높은 경쟁 | 왼쪽 위: 높은 성과 + 낮은 경쟁 (최적)")

        with tab3:
            # Shorts ratio by cluster
            fig = px.bar(
                df,
                x="클러스터",
                y="Shorts 비중",
                title="클러스터별 Shorts 비중",
                labels={"Shorts 비중": "비중"}
            )
            st.plotly_chart(fig, width="stretch")

            # Video count vs Shorts ratio
            video_shorts_data = []
            for cluster in clusters:
                video_shorts_data.append({
                    "클러스터": cluster['label'][:30],
                    "영상 수": cluster['video_count'],
                    "Shorts 비중": cluster['shorts_ratio'] * 100
                })

            vs_df = pd.DataFrame(video_shorts_data)

            fig = px.scatter(
                vs_df,
                x="영상 수",
                y="Shorts 비중",
                text="클러스터",
                title="클러스터 크기 vs Shorts 비중",
                labels={"영상 수": "영상 수", "Shorts 비중": "Shorts 비중 (%)"}
            )
            fig.update_traces(textposition='top center')
            st.plotly_chart(fig, width="stretch")

        # Detailed cluster view
        st.markdown("---")
        st.subheader("🔍 클러스터 상세")

        selected_cluster_label = st.selectbox(
            "클러스터 선택",
            [c['label'] for c in clusters]
        )

        selected_cluster = next(c for c in clusters if c['label'] == selected_cluster_label)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"#### {selected_cluster_label}")

            st.markdown(f"""
            - **영상 수:** {selected_cluster['video_count']}
            - **중앙 조회수:** {selected_cluster['median_views']:,}
            - **평균 조회수:** {selected_cluster['avg_views']:,}
            - **고유 채널:** {selected_cluster['unique_channels']}
            - **Top10 집중도:** {selected_cluster['top10_concentration'] * 100:.1f}%
            - **Shorts 비중:** {selected_cluster['shorts_ratio'] * 100:.1f}%
            - **종합 점수:** {selected_cluster['final_score']:.2f}
            """)

        with col2:
            # Score badge
            score = selected_cluster['final_score']

            if score > 3:
                badge = "🟢 진입 추천"
                color = "green"
            elif score > 1:
                badge = "🟡 보통"
                color = "orange"
            else:
                badge = "🔴 경쟁 치열"
                color = "red"

            st.markdown(f"### {badge}")
            st.markdown(f"**점수:** {score:.2f}")

        # Sample videos
        st.markdown("#### 📹 대표 영상 (조회수 상위 5개)")

        sample_videos = selected_cluster['sample_videos']

        if sample_videos:
            # Display videos in grid with thumbnails
            cols_per_row = 5
            for i in range(0, len(sample_videos), cols_per_row):
                cols = st.columns(cols_per_row)

                for j in range(cols_per_row):
                    idx = i + j
                    if idx < len(sample_videos):
                        video = sample_videos[idx]

                        with cols[j]:
                            # Thumbnail
                            thumbnail_url = f"https://img.youtube.com/vi/{video['video_id']}/hqdefault.jpg"
                            st.image(thumbnail_url, use_container_width=True)

                            # Play button
                            if st.button(
                                "▶️ 재생",
                                key=f"play_sample_{selected_cluster['cluster_index']}_{idx}",
                                use_container_width=True
                            ):
                                show_video_player(video['video_id'], video['title'])

                            # Video info
                            st.markdown(f"**{video['title'][:40]}{'...' if len(video['title']) > 40 else ''}**")

                            # Channel name
                            channel_name = video.get('channel_title', 'Unknown')
                            st.caption(f"📺 {channel_name[:30]}{'...' if len(channel_name) > 30 else ''}")

                            # Subscriber count
                            subscriber_count = video.get('subscriber_count', 0)
                            if subscriber_count > 0:
                                if subscriber_count >= 1000000:
                                    st.caption(f"👥 {subscriber_count / 1000000:.1f}M 구독자")
                                elif subscriber_count >= 1000:
                                    st.caption(f"👥 {subscriber_count / 1000:.1f}K 구독자")
                                else:
                                    st.caption(f"👥 {subscriber_count:,} 구독자")

                            st.caption(f"👁️ {video['view_count']:,}")

                            # Upload date
                            upload_date = video.get('published_at', '')[:10] if video.get('published_at') else "N/A"
                            if upload_date != "N/A":
                                st.caption(f"📅 {upload_date}")
        else:
            st.info("대표 영상이 없습니다.")

        # Sample channels
        st.markdown("#### 📺 주요 채널 (영상 수 상위 5개)")

        sample_channels = selected_cluster['sample_channels']

        if sample_channels:
            for i, ch in enumerate(sample_channels):
                youtube_url = f"https://youtube.com/channel/{ch['channel_id']}"
                channel_name = ch.get('channel_title', 'Unknown')
                st.markdown(
                    f"**{i+1}. {channel_name}** - "
                    f"이 클러스터 영상 {ch['video_count']}개 | "
                    f"[🔗 채널 보기]({youtube_url})"
                )
        else:
            st.info("주요 채널 정보가 없습니다.")

        # All Videos Section
        st.markdown("---")
        st.markdown("---")
        st.subheader("📹 수집된 전체 영상 목록")

        if st.session_state.all_videos:
            all_videos = st.session_state.all_videos

            st.markdown(f"**총 {len(all_videos)}개의 영상이 수집되었습니다.**")

            # Filter options
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

            with col1:
                filter_cluster = st.selectbox(
                    "클러스터 필터",
                    ["전체"] + [f"#{i}" for i in range(len(clusters))],
                    help="특정 클러스터의 영상만 보기"
                )

            with col2:
                filter_type = st.selectbox(
                    "영상 유형",
                    ["전체", "Shorts만 (≤60초)", "일반 영상만 (>60초)"]
                )

            with col3:
                sort_videos_by = st.selectbox(
                    "정렬",
                    ["조회수 높은순", "조회수 낮은순", "최신순", "오래된순"]
                )

            with col4:
                view_mode = st.selectbox(
                    "보기",
                    ["그리드", "테이블"]
                )

            # Build filtered video list
            filtered_videos = []
            for video in all_videos:
                # Apply cluster filter
                if filter_cluster != "전체":
                    cluster_num = int(filter_cluster.lstrip("#"))
                    if video.get('cluster_index', -1) != cluster_num:
                        continue

                # Apply type filter
                is_short = video['duration_seconds'] <= 60
                if filter_type == "Shorts만 (≤60초)" and not is_short:
                    continue
                if filter_type == "일반 영상만 (>60초)" and is_short:
                    continue

                filtered_videos.append(video)

            if filtered_videos:
                # Sort videos
                if sort_videos_by == "조회수 높은순":
                    filtered_videos.sort(key=lambda x: x['view_count'], reverse=True)
                elif sort_videos_by == "조회수 낮은순":
                    filtered_videos.sort(key=lambda x: x['view_count'], reverse=False)
                elif sort_videos_by == "최신순":
                    filtered_videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)
                elif sort_videos_by == "오래된순":
                    filtered_videos.sort(key=lambda x: x.get('published_at', ''), reverse=False)

                st.markdown(f"**필터 결과: {len(filtered_videos)}개 영상**")

                # Display based on view mode
                if view_mode == "그리드":
                    # Grid view with thumbnails
                    cols_per_row = 5
                    for i in range(0, len(filtered_videos), cols_per_row):
                        cols = st.columns(cols_per_row)

                        for j in range(cols_per_row):
                            idx = i + j
                            if idx < len(filtered_videos):
                                video = filtered_videos[idx]
                                is_short = video['duration_seconds'] <= 60

                                with cols[j]:
                                    # Thumbnail
                                    thumbnail_url = f"https://img.youtube.com/vi/{video['video_id']}/hqdefault.jpg"
                                    st.image(thumbnail_url, use_container_width=True)

                                    # Play button
                                    if st.button(
                                        "▶️ 재생",
                                        key=f"play_all_{idx}",
                                        use_container_width=True
                                    ):
                                        show_video_player(video['video_id'], video['title'])

                                    # Video info
                                    st.markdown(f"**{video['title'][:40]}{'...' if len(video['title']) > 40 else ''}**")

                                    # Channel name
                                    channel_name = video.get('channel_title', 'Unknown')
                                    st.caption(f"📺 {channel_name[:30]}{'...' if len(channel_name) > 30 else ''}")

                                    # Subscriber count
                                    subscriber_count = video.get('subscriber_count', 0)
                                    if subscriber_count > 0:
                                        if subscriber_count >= 1000000:
                                            st.caption(f"👥 {subscriber_count / 1000000:.1f}M 구독자")
                                        elif subscriber_count >= 1000:
                                            st.caption(f"👥 {subscriber_count / 1000:.1f}K 구독자")
                                        else:
                                            st.caption(f"👥 {subscriber_count:,} 구독자")

                                    video_type = "🩳 Shorts" if is_short else "🎥 일반"
                                    st.caption(f"{video_type} | {video['duration_seconds']}초")
                                    st.caption(f"👁️ {video['view_count']:,}")

                                    # Upload date
                                    upload_date = video.get('published_at', '')[:10] if video.get('published_at') else "N/A"
                                    st.caption(f"📅 {upload_date}")

                                    st.caption(f"#{video.get('cluster_index', '?')}")
                                    st.markdown("---")
                else:
                    # Table view
                    videos_table = []
                    for video in filtered_videos:
                        is_short = video['duration_seconds'] <= 60
                        videos_table.append({
                            "클러스터": f"#{video.get('cluster_index', '?')}",
                            "제목": video['title'][:60] + "..." if len(video['title']) > 60 else video['title'],
                            "채널명": video.get('channel_title', 'Unknown')[:30],
                            "구독자 수": video.get('subscriber_count', 0),
                            "조회수": video['view_count'],
                            "좋아요": video.get('like_count', 0),
                            "댓글": video.get('comment_count', 0),
                            "길이 (초)": video['duration_seconds'],
                            "유형": "Shorts" if is_short else "일반",
                            "게시일": video.get('published_at', '')[:10] if video.get('published_at') else "N/A",
                            "YouTube 링크": f"https://youtube.com/watch?v={video['video_id']}"
                        })

                    videos_df = pd.DataFrame(videos_table)

                    st.dataframe(
                        videos_df,
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "구독자 수": st.column_config.NumberColumn(format="%d"),
                            "조회수": st.column_config.NumberColumn(format="%d"),
                            "좋아요": st.column_config.NumberColumn(format="%d"),
                            "댓글": st.column_config.NumberColumn(format="%d"),
                            "YouTube 링크": st.column_config.LinkColumn("링크")
                        },
                        height=600
                    )

                # Download button
                csv_data = []
                for video in filtered_videos:
                    is_short = video['duration_seconds'] <= 60
                    csv_data.append({
                        "클러스터": f"#{video.get('cluster_index', '?')}",
                        "제목": video['title'],
                        "채널명": video.get('channel_title', 'Unknown'),
                        "구독자 수": video.get('subscriber_count', 0),
                        "조회수": video['view_count'],
                        "좋아요": video.get('like_count', 0),
                        "댓글": video.get('comment_count', 0),
                        "길이 (초)": video['duration_seconds'],
                        "유형": "Shorts" if is_short else "일반",
                        "게시일": video.get('published_at', '')[:10] if video.get('published_at') else "N/A",
                        "YouTube 링크": f"https://youtube.com/watch?v={video['video_id']}"
                    })

                csv_df = pd.DataFrame(csv_data)
                csv = csv_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 CSV로 다운로드",
                    data=csv,
                    file_name=f"niche_videos_{len(filtered_videos)}.csv",
                    mime="text/csv",
                )

            else:
                st.info("필터 조건에 맞는 영상이 없습니다.")

        else:
            st.info("전체 영상 목록은 캐시된 결과에서는 제공되지 않습니다. 새로 탐색을 실행해주세요.")

        # Channel Extraction Section
        if st.session_state.all_videos:
            st.markdown("---")
            st.markdown("---")
            st.subheader("📺 채널 추출 및 일괄 추가")

            all_videos = st.session_state.all_videos

            # Extract unique channels and their stats
            channel_stats = {}
            for video in all_videos:
                channel_id = video.get('channel_id')
                channel_title = video.get('channel_title', 'Unknown')

                if not channel_id:
                    continue

                if channel_id not in channel_stats:
                    channel_stats[channel_id] = {
                        'channel_id': channel_id,
                        'channel_title': channel_title,
                        'video_count': 0,
                        'total_views': 0,
                        'total_likes': 0,
                        'shorts_count': 0
                    }

                stats = channel_stats[channel_id]
                stats['video_count'] += 1
                stats['total_views'] += video.get('view_count', 0)
                stats['total_likes'] += video.get('like_count', 0)
                if video.get('duration_seconds', 0) <= 60:
                    stats['shorts_count'] += 1

            # Calculate averages
            channel_list = []
            for ch_id, stats in channel_stats.items():
                stats['avg_views'] = int(stats['total_views'] / stats['video_count']) if stats['video_count'] > 0 else 0
                stats['shorts_ratio'] = stats['shorts_count'] / stats['video_count'] if stats['video_count'] > 0 else 0
                channel_list.append(stats)

            if channel_list:
                st.markdown(f"**발견된 고유 채널: {len(channel_list)}개**")

                # Filters
                col1, col2, col3 = st.columns(3)

                with col1:
                    min_videos = st.number_input(
                        "최소 영상 수",
                        min_value=1,
                        max_value=50,
                        value=2,
                        help="이 검색에서 해당 채널의 영상이 최소 몇 개 이상"
                    )

                with col2:
                    min_avg_views = st.number_input(
                        "최소 평균 조회수",
                        min_value=0,
                        max_value=10000000,
                        value=10000,
                        step=10000,
                        help="평균 조회수가 이 값 이상인 채널만"
                    )

                with col3:
                    shorts_only = st.checkbox(
                        "Shorts 위주 채널만 (80% 이상)",
                        value=False,
                        help="Shorts 비중이 80% 이상인 채널만 표시"
                    )

                # Apply filters
                filtered_channels = [
                    ch for ch in channel_list
                    if ch['video_count'] >= min_videos
                    and ch['avg_views'] >= min_avg_views
                    and (not shorts_only or ch['shorts_ratio'] >= 0.8)
                ]

                # Sort by average views
                filtered_channels.sort(key=lambda x: x['avg_views'], reverse=True)

                st.markdown(f"**필터 결과: {len(filtered_channels)}개 채널**")

                if filtered_channels:
                    # Check which channels already exist in DB
                    existing_channels = {ch.youtube_channel_id: ch for ch in db.get_all_channels()}

                    # Build channel table with checkboxes
                    st.markdown("#### 채널 선택")

                    # Select all checkbox
                    select_all = st.checkbox("전체 선택", value=False)

                    # Create selection state
                    if 'selected_channels' not in st.session_state:
                        st.session_state.selected_channels = set()

                    if select_all:
                        st.session_state.selected_channels = {ch['channel_id'] for ch in filtered_channels if ch['channel_id'] not in existing_channels}

                    # Display channels
                    for ch in filtered_channels[:50]:  # Limit to 50 to avoid too many checkboxes
                        already_exists = ch['channel_id'] in existing_channels

                        col_check, col_info = st.columns([1, 9])

                        with col_check:
                            if already_exists:
                                st.markdown("✓")
                            else:
                                is_selected = st.checkbox(
                                    "선택",
                                    value=ch['channel_id'] in st.session_state.selected_channels,
                                    key=f"ch_{ch['channel_id']}",
                                    label_visibility="collapsed"
                                )
                                if is_selected:
                                    st.session_state.selected_channels.add(ch['channel_id'])
                                else:
                                    st.session_state.selected_channels.discard(ch['channel_id'])

                        with col_info:
                            status = " ✅ (이미 추가됨)" if already_exists else ""
                            st.markdown(
                                f"**{ch['channel_title']}**{status} | "
                                f"영상: {ch['video_count']}개 | "
                                f"평균 조회수: {ch['avg_views']:,} | "
                                f"Shorts: {ch['shorts_ratio']*100:.0f}% | "
                                f"[링크](https://youtube.com/channel/{ch['channel_id']})"
                            )

                    if len(filtered_channels) > 50:
                        st.info(f"⚠️ 표시 제한: 상위 50개 채널만 표시됩니다. (총 {len(filtered_channels)}개)")

                    # Add selected channels button
                    st.markdown("---")

                    selected_count = len(st.session_state.selected_channels)

                    if selected_count > 0:
                        if st.button(f"✅ 선택한 {selected_count}개 채널 추가", type="primary"):
                            progress_placeholder = st.empty()
                            status_placeholder = st.empty()

                            success_count = 0
                            failed_count = 0

                            selected_channel_ids = list(st.session_state.selected_channels)

                            for idx, channel_id in enumerate(selected_channel_ids, 1):
                                progress_placeholder.progress(
                                    idx / len(selected_channel_ids),
                                    text=f"진행 중: {idx}/{len(selected_channel_ids)}"
                                )

                                try:
                                    result = jobs.fetch_channel_data(
                                        channel_id,
                                        force_refresh=False,
                                        progress_callback=lambda msg: None
                                    )

                                    if result:
                                        success_count += 1
                                    else:
                                        failed_count += 1

                                    status_placeholder.info(
                                        f"✓ {success_count}개 성공, {failed_count}개 실패"
                                    )

                                except Exception as e:
                                    failed_count += 1
                                    status_placeholder.warning(
                                        f"✓ {success_count}개 성공, {failed_count}개 실패"
                                    )

                            progress_placeholder.empty()
                            st.success(f"🎉 완료! {success_count}개 채널이 추가되었습니다.")

                            # Clear selection
                            st.session_state.selected_channels = set()
                            st.rerun()
                    else:
                        st.info("추가할 채널을 선택해주세요.")

                else:
                    st.info("필터 조건에 맞는 채널이 없습니다. 필터를 조정해보세요.")

            else:
                st.warning("채널 정보를 추출할 수 없습니다.")

    except Exception as e:
        st.error(f"결과를 불러오는 중 오류가 발생했습니다: {e}")

else:
    st.info("👆 위에서 키워드를 입력하고 탐색을 시작해보세요!")

    st.markdown("""
    ### 사용 가이드

    1. **키워드 입력**: 탐색하고 싶은 니치의 키워드를 입력하세요.
       - 예: "cute cats", "cooking recipes", "workout shorts"
       - 영어 키워드가 더 많은 결과를 제공합니다.

    2. **설정 조정**:
       - **최대 영상 수**: 많을수록 정확하지만 시간이 오래 걸립니다 (권장: 200~300)
       - **클러스터 수**: 세분화 정도 (권장: 6~10)
       - **캐시 사용**: 동일한 검색을 24시간 내 재실행 시 빠르게 결과 확인

    3. **결과 분석**:
       - 종합 점수가 높은 클러스터가 진입하기 좋은 니치입니다.
       - 성과는 높지만 경쟁이 낮은 클러스터를 찾아보세요.
       - 대표 영상과 채널을 참고하여 콘텐츠 방향을 정하세요.

    4. **활용 팁**:
       - 여러 키워드로 탐색하여 트렌드를 파악하세요.
       - Shorts 중심 콘텐츠라면 Shorts 비중이 높은 클러스터에 주목하세요.
       - 발견한 채널을 Dashboard에 추가하여 지속적으로 모니터링하세요.
    """)

# Footer
st.markdown("---")
st.caption("💡 팁: AI가 자동으로 비슷한 영상들을 그룹화하여 숨겨진 니치를 발견해줍니다!")
