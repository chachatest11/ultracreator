"""
NexLev Mini - YouTube Analytics Dashboard
Main application entry point
"""
import streamlit as st
from core import db

# Page config
st.set_page_config(
    page_title="홈 - NexLev Mini",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
db.init_db()

# Custom CSS to rename "Home" to "홈" in sidebar
st.markdown("""
<style>
    /* Hide the default Home label and replace with 홈 */
    [data-testid="stSidebarNav"] li:first-child a div[data-testid="stMarkdownContainer"] p {
        font-size: 0;
    }
    [data-testid="stSidebarNav"] li:first-child a div[data-testid="stMarkdownContainer"] p::before {
        content: "🏠 홈";
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF0000;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Main page
st.markdown('<div class="main-header">📊 NexLev Mini</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">YouTube 채널 분석 & 니치 탐색 도구 (해외 양산형 쇼츠 리서치)</div>',
    unsafe_allow_html=True
)

# Welcome message
st.markdown("""
### 환영합니다! 👋

**NexLev Mini**는 YouTube 채널과 영상을 분석하여 데이터 기반 의사결정을 돕는 도구입니다.

#### 주요 기능:

1. **📊 채널 목록** - 관심 채널 관리 및 주요 지표 모니터링
   - 채널 추가/삭제/갱신
   - 핵심 지표 한눈에 확인
   - Shorts 중심 필터링

2. **📈 상세 분석** - 채널 상세 분석
   - 최근 50개 영상 데이터
   - 업로드 패턴 분석
   - 조회수 분포 시각화

3. **⭐ 그룹 관리** - 채널 그룹 관리 및 비교
   - 그룹 생성/관리
   - 채널 간 성과 비교
   - 패턴 분석 (요일/시간대/제목길이)

4. **🎯 트렌드 분석** - 니치 키워드 탐색
   - 키워드 기반 영상 수집 (200~500개)
   - AI 클러스터링으로 트렌드 발견
   - 진입 가능성 점수화

#### 시작하기:

왼쪽 사이드바에서 원하는 페이지를 선택하세요.

- **📊 채널 목록**에서 첫 채널을 추가해보세요!
- YouTube 채널 ID, 핸들(@username), 또는 URL을 입력하면 됩니다.

#### 설정:

- `.env` 파일에 `YOUTUBE_API_KEY`를 설정했는지 확인하세요.
- API 키는 [Google Cloud Console](https://console.cloud.google.com/)에서 발급받을 수 있습니다.
""")

# Quick stats
col1, col2, col3 = st.columns(3)

channels = db.get_all_channels()
watchlists = db.get_all_watchlists()

with col1:
    st.metric(label="등록된 채널", value=len(channels))

with col2:
    st.metric(label="워치리스트", value=len(watchlists))

with col3:
    total_videos = sum(
        len(db.get_videos_by_channel(ch.id, limit=50))
        for ch in channels
    )
    st.metric(label="수집된 영상", value=total_videos)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    Made with ❤️ for YouTube Shorts Researchers | Powered by Streamlit & YouTube Data API v3
</div>
""", unsafe_allow_html=True)
