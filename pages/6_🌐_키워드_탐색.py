"""
YouTube Multilingual Keyword Explorer
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import db

# Try to import trends module - show error if dependencies not installed
try:
    from core.trends import TrendsExplorer, YOUTUBE_CATEGORIES, LANGUAGES
    DEPENDENCIES_INSTALLED = True
except ImportError as e:
    DEPENDENCIES_INSTALLED = False
    IMPORT_ERROR = str(e)

# Page config
st.set_page_config(
    page_title="키워드 탐색 | NexLev Mini",
    page_icon="🌐",
    layout="wide"
)

# Initialize database
db.init_db()

# Page title
st.title("🌐 YouTube 다국어 키워드 검색기")
st.markdown("""
카테고리/키워드 입력 시 100개의 세부 주제 및 키워드를 7개 언어로 번역합니다.
""")

# Check if dependencies are installed
if not DEPENDENCIES_INSTALLED:
    st.error(f"""
    ❌ **필수 패키지가 설치되지 않았습니다**

    이 기능을 사용하려면 다음 패키지를 설치해야 합니다:

    ```bash
    pip install pytrends deepl deep-translator
    ```

    또는 전체 의존성 설치:

    ```bash
    pip install -r requirements.txt
    ```

    **오류 세부정보**: {IMPORT_ERROR}
    """)
    st.stop()

st.markdown("---")

# Category selection
st.markdown("### 🎯 카테고리 선택")

# Create category buttons
categories = list(YOUTUBE_CATEGORIES.keys())

# Display categories in rows
cols_per_row = 4
category_rows = [categories[i:i + cols_per_row] for i in range(0, len(categories), cols_per_row)]

selected_category = None

for row in category_rows:
    cols = st.columns(cols_per_row)
    for i, category in enumerate(row):
        with cols[i]:
            if st.button(category, use_container_width=True, key=f"cat_{category}"):
                selected_category = category
                st.session_state.selected_category = category

# Use session state to persist selection
if 'selected_category' in st.session_state:
    selected_category = st.session_state.selected_category

if selected_category:
    st.success(f"✅ 선택된 카테고리: **{selected_category}**")

st.markdown("---")

# Keyword input
st.markdown("### 🔍 키워드 입력 (선택사항)")

with st.form(key="keyword_search_form"):
    col1, col2 = st.columns([3, 1])

    with col1:
        custom_keyword = st.text_input(
            "여기에 원하는 키워드를 직접 입력하세요 (예: 여행, 게임, 요리)",
            placeholder="키워드 입력...",
            help="카테고리와 함께 또는 단독으로 키워드를 입력할 수 있습니다."
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_button = st.form_submit_button("🔎 검색", type="primary", use_container_width=True)

st.markdown("---")

# Advanced settings
with st.expander("⚙️ 고급 설정"):
    col1, col2 = st.columns(2)

    with col1:
        num_keywords = st.slider(
            "생성할 키워드 수",
            min_value=10,
            max_value=200,
            value=100,
            step=10,
            help="더 많은 키워드를 생성하면 시간이 더 걸립니다."
        )

    with col2:
        use_cache = st.checkbox(
            "캐시 사용 (24시간)",
            value=True,
            help="같은 카테고리에 대해 24시간 이내 결과를 재사용합니다."
        )

st.markdown("---")

# Search logic
if search_button or 'keyword_results' in st.session_state:
    # Determine what to search for
    search_term = None

    if custom_keyword:
        search_term = custom_keyword
        search_label = custom_keyword
    elif selected_category:
        search_term = selected_category
        search_label = f"{selected_category} 카테고리"
    else:
        st.warning("⚠️ 카테고리를 선택하거나 키워드를 입력해주세요.")
        st.stop()

    # Check cache if enabled
    cached_results = None
    if use_cache and selected_category and not custom_keyword:
        cached_results = db.get_trending_keywords(selected_category, max_age_hours=24)

        if cached_results:
            st.info("📦 캐시된 결과를 불러왔습니다. (24시간 이내)")
            st.session_state.keyword_results = cached_results
            st.session_state.search_label = search_label

    # Fetch new results if not cached
    if search_button and not cached_results:
        with st.spinner(f"🔍 '{search_label}'에 대한 트렌딩 키워드를 수집하고 번역하는 중..."):
            try:
                explorer = TrendsExplorer()

                # Get trending keywords with translations
                if selected_category:
                    results = explorer.explore_category_with_translations(
                        selected_category,
                        num_keywords=num_keywords
                    )
                else:
                    # For custom keyword without category, just translate it
                    from core.trends import TranslationManager
                    translator = TranslationManager()
                    translations = translator.translate_to_all_languages(custom_keyword)
                    results = [{
                        'keyword': custom_keyword,
                        'translations': translations
                    }]

                # Save to session state
                st.session_state.keyword_results = results
                st.session_state.search_label = search_label

                # Save to cache if category-based search
                if selected_category and not custom_keyword:
                    db.save_trending_keywords(selected_category, results)

                st.success(f"✅ {len(results)}개의 키워드를 성공적으로 수집했습니다!")

            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {e}")
                st.stop()

    # Display results
    if 'keyword_results' in st.session_state:
        results = st.session_state.keyword_results
        search_label = st.session_state.search_label

        st.markdown(f"### 📊 **'{search_label}'** 주제에 대한 연관 키워드 ({len(results)}개)")

        # Language header
        st.markdown("#### 🗣️ 지원 언어")
        lang_cols = st.columns(7)
        language_names = list(LANGUAGES.keys())

        for i, lang in enumerate(language_names):
            with lang_cols[i]:
                if lang == "한국어":
                    st.markdown(f"**🇰🇷 {lang}**")
                elif lang == "영어":
                    st.markdown(f"**🇺🇸 {lang}**")
                elif lang == "일본어":
                    st.markdown(f"**🇯🇵 {lang}**")
                elif lang == "중국어":
                    st.markdown(f"**🇨🇳 {lang}**")
                elif lang == "스페인어":
                    st.markdown(f"**🇪🇸 {lang}**")
                elif lang == "힌디어":
                    st.markdown(f"**🇮🇳 {lang}**")
                elif lang == "러시아어":
                    st.markdown(f"**🇷🇺 {lang}**")

        st.markdown("---")

        # Display keywords table
        st.markdown("#### 📋 키워드 목록")

        # Prepare table data
        table_data = []
        for idx, item in enumerate(results, start=1):
            keyword = item['keyword']
            translations = item['translations']

            row = {
                "순위": idx,
                "🇰🇷 한국어": translations.get("한국어", keyword),
                "🇺🇸 영어": translations.get("영어", ""),
                "🇯🇵 일본어": translations.get("일본어", ""),
                "🇨🇳 중국어": translations.get("중국어", ""),
                "🇪🇸 스페인어": translations.get("스페인어", ""),
                "🇮🇳 힌디어": translations.get("힌디어", ""),
                "🇷🇺 러시아어": translations.get("러시아어", "")
            }
            table_data.append(row)

        df = pd.DataFrame(table_data)

        # Display table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=600
        )

        # Download button
        st.markdown("#### 💾 다운로드")

        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label=f"📥 CSV로 다운로드 ({len(results)}개 키워드)",
            data=csv,
            file_name=f"youtube_keywords_{search_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Statistics
        st.markdown("---")
        st.markdown("#### 📈 통계")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("총 키워드 수", f"{len(results)}개")

        with col2:
            st.metric("지원 언어", "7개 언어")

        with col3:
            total_translations = len(results) * 7
            st.metric("총 번역 수", f"{total_translations:,}개")

else:
    # Initial state - show instructions
    st.info("""
    ### 📌 사용 방법

    1. **카테고리 선택**: 위에서 YouTube 카테고리를 선택하세요.
    2. **키워드 입력** (선택사항): 특정 키워드를 직접 입력할 수 있습니다.
    3. **검색 버튼 클릭**: '검색' 버튼을 눌러 트렌딩 키워드를 수집하고 번역합니다.
    4. **결과 확인**: 7개 언어로 번역된 키워드 목록을 확인하세요.
    5. **CSV 다운로드**: 필요한 경우 결과를 CSV 파일로 다운로드할 수 있습니다.

    ---

    ### 💡 팁

    - **캐시 기능**: 같은 카테고리에 대해 24시간 동안 결과가 캐시됩니다.
    - **DeepL API**: `.env` 파일에 `DEEPL_API_KEY`를 설정하면 더 높은 품질의 번역을 사용할 수 있습니다.
    - **키워드 수**: 고급 설정에서 생성할 키워드 수를 조정할 수 있습니다 (10~200개).
    """)
