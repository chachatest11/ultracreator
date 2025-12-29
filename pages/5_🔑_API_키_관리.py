"""
API Key Manager - Manage YouTube API Keys
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from core.api_key_storage import get_storage

st.set_page_config(page_title="🔑 API 키 관리", page_icon="🔑", layout="wide")

st.title("🔑 API 키 관리")
st.markdown("YouTube Data API 키 관리 - UI에서 직접 추가/삭제/활성화")

# Get storage instance
storage = get_storage()

# Initialize session state
if 'refresh_trigger' not in st.session_state:
    st.session_state.refresh_trigger = 0

# Info section
with st.expander("ℹ️ API 키 관리 정보", expanded=False):
    st.markdown("""
    ### API 키 설정 방법

    **Option 1: UI에서 관리 (이 페이지)**
    - ✅ 편리한 추가/삭제/활성화/비활성화
    - ✅ 키별 이름 설정 및 상태 확인
    - ✅ 재시작 없이 즉시 적용

    **Option 2: .env 파일**
    - `.env` 파일에 `YOUTUBE_API_KEY` 또는 `YOUTUBE_API_KEYS` 설정
    - 앱 재시작 필요

    ### 우선순위
    UI 키와 .env 키가 모두 사용되며, 중복되지 않는 키만 추가됩니다.

    ### 보안
    - 키는 base64로 인코딩되어 `.api_keys.json` 파일에 저장됩니다
    - 파일 권한은 소유자만 읽기/쓰기 가능하도록 설정됩니다 (Unix 계열)
    - ⚠️ **주의**: 공유 환경에서는 주의가 필요합니다
    """)

st.markdown("---")

# Add new key section
st.subheader("➕ 새 API 키 추가")

col1, col2 = st.columns([3, 1])

with col1:
    new_key = st.text_input(
        "API Key",
        type="password",
        placeholder="AIzaSy...",
        help="YouTube Data API v3 키를 입력하세요"
    )

with col2:
    key_name = st.text_input(
        "키 이름 (선택사항)",
        placeholder="예: Main Key"
    )

col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("➕ 키 추가", type="primary", width="stretch"):
        if new_key:
            if storage.add_key(new_key, key_name):
                st.success(f"✓ API 키가 추가되었습니다: {key_name or '(이름 없음)'}")
                st.session_state.refresh_trigger += 1
                st.rerun()
            else:
                st.error("✗ 이미 존재하는 키이거나 추가에 실패했습니다.")
        else:
            st.warning("API 키를 입력해주세요.")

with col2:
    # Bulk import
    if st.button("📥 일괄 가져오기", width="stretch"):
        st.session_state.show_import = True

# Bulk import dialog
if st.session_state.get('show_import', False):
    with st.form("import_keys_form"):
        st.markdown("#### 여러 키 일괄 가져오기")
        bulk_keys = st.text_area(
            "API 키들 (쉼표로 구분)",
            placeholder="AIzaSy...,AIzaSy...,AIzaSy...",
            height=100
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("가져오기", type="primary", width="stretch")
        with col2:
            cancel = st.form_submit_button("취소", width="stretch")

        if submit and bulk_keys:
            added_count = storage.import_keys_from_string(bulk_keys)
            st.success(f"✓ {added_count}개의 키가 추가되었습니다.")
            st.session_state.show_import = False
            st.session_state.refresh_trigger += 1
            st.rerun()

        if cancel:
            st.session_state.show_import = False
            st.rerun()

st.markdown("---")

# Display existing keys
st.subheader("📋 등록된 API 키")

keys = storage.get_all_keys()

if not keys:
    st.info("등록된 API 키가 없습니다. 위에서 키를 추가해주세요.")
else:
    # Summary stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("총 키 개수", len(keys))

    with col2:
        active_count = sum(1 for k in keys if k['enabled'])
        st.metric("활성 키", active_count, delta=f"{len(keys) - active_count} 비활성")

    with col3:
        total_quota = active_count * 10000
        st.metric("일일 총 쿼터", f"{total_quota:,} 유닛")

    st.markdown("---")

    # Display keys in table format
    for key_data in keys:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

            with col1:
                # Key name and masked key
                status_icon = "🟢" if key_data['enabled'] else "🔴"
                st.markdown(f"### {status_icon} {key_data['name']}")

                # Show masked key
                masked_key = key_data['key'][:10] + "..." + key_data['key'][-4:] if len(key_data['key']) > 14 else "***"
                st.caption(f"🔑 {masked_key}")

                # Show created date
                if key_data['created_at']:
                    try:
                        created = datetime.fromisoformat(key_data['created_at'])
                        st.caption(f"📅 추가일: {created.strftime('%Y-%m-%d %H:%M')}")
                    except:
                        pass

                # Show last used
                if key_data['last_used']:
                    try:
                        last_used = datetime.fromisoformat(key_data['last_used'])
                        st.caption(f"🕐 최근 사용: {last_used.strftime('%Y-%m-%d %H:%M')}")
                    except:
                        pass

            with col2:
                st.markdown("**상태**")
                if key_data['enabled']:
                    st.success("✅ 활성")
                else:
                    st.warning("⏸️ 비활성")

            with col3:
                st.markdown("**작업**")

                # Toggle enable/disable
                if key_data['enabled']:
                    if st.button("비활성화", key=f"disable_{key_data['id']}", width="stretch"):
                        storage.toggle_key(key_data['id'], False)
                        st.success("키가 비활성화되었습니다.")
                        st.session_state.refresh_trigger += 1
                        st.rerun()
                else:
                    if st.button("활성화", key=f"enable_{key_data['id']}", type="primary", width="stretch"):
                        storage.toggle_key(key_data['id'], True)
                        st.success("키가 활성화되었습니다.")
                        st.session_state.refresh_trigger += 1
                        st.rerun()

            with col4:
                st.markdown("**관리**")

                # Rename button
                if st.button("이름 변경", key=f"rename_{key_data['id']}", width="stretch"):
                    st.session_state[f"rename_mode_{key_data['id']}"] = True
                    st.rerun()

                # Delete button
                if st.button("🗑️ 삭제", key=f"delete_{key_data['id']}", width="stretch"):
                    st.session_state[f"confirm_delete_{key_data['id']}"] = True
                    st.rerun()

            # Rename dialog
            if st.session_state.get(f"rename_mode_{key_data['id']}", False):
                with st.form(f"rename_form_{key_data['id']}"):
                    new_name = st.text_input("새 이름", value=key_data['name'])
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("저장", type="primary", width="stretch"):
                            storage.rename_key(key_data['id'], new_name)
                            st.session_state[f"rename_mode_{key_data['id']}"] = False
                            st.success("이름이 변경되었습니다.")
                            st.session_state.refresh_trigger += 1
                            st.rerun()
                    with col2:
                        if st.form_submit_button("취소", width="stretch"):
                            st.session_state[f"rename_mode_{key_data['id']}"] = False
                            st.rerun()

            # Delete confirmation
            if st.session_state.get(f"confirm_delete_{key_data['id']}", False):
                st.warning(f"⚠️ 정말로 '{key_data['name']}' 키를 삭제하시겠습니까?")
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("✓ 삭제", key=f"confirm_yes_{key_data['id']}", type="primary", width="stretch"):
                        storage.remove_key(key_data['id'])
                        st.session_state[f"confirm_delete_{key_data['id']}"] = False
                        st.success("키가 삭제되었습니다.")
                        st.session_state.refresh_trigger += 1
                        st.rerun()
                with col2:
                    if st.button("✗ 취소", key=f"confirm_no_{key_data['id']}", width="stretch"):
                        st.session_state[f"confirm_delete_{key_data['id']}"] = False
                        st.rerun()

            st.markdown("---")

# Advanced actions
st.markdown("---")
st.subheader("⚙️ 고급 작업")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 현재 상태 새로고침", width="stretch"):
        st.session_state.refresh_trigger += 1
        st.rerun()

with col2:
    if st.button("📊 키 상태 요약", width="stretch"):
        st.session_state.show_summary = True

with col3:
    if st.button("🗑️ 모든 키 삭제", type="secondary", width="stretch"):
        st.session_state.confirm_clear_all = True

# Summary dialog
if st.session_state.get('show_summary', False):
    st.markdown("### 📊 키 상태 요약")

    summary_data = []
    for i, key_data in enumerate(keys):
        summary_data.append({
            "번호": i + 1,
            "이름": key_data['name'],
            "상태": "활성" if key_data['enabled'] else "비활성",
            "키 (마스킹)": key_data['key'][:10] + "..." + key_data['key'][-4:],
            "추가일": key_data['created_at'][:10] if key_data['created_at'] else "N/A"
        })

    if summary_data:
        df = pd.DataFrame(summary_data)
        st.dataframe(df, width="stretch", hide_index=True)

    if st.button("닫기"):
        st.session_state.show_summary = False
        st.rerun()

# Clear all confirmation
if st.session_state.get('confirm_clear_all', False):
    st.error("⚠️ 경고: 모든 키를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다!")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("✓ 모두 삭제", type="primary", width="stretch"):
            storage.clear_all_keys()
            st.session_state.confirm_clear_all = False
            st.success("모든 키가 삭제되었습니다.")
            st.session_state.refresh_trigger += 1
            st.rerun()
    with col2:
        if st.button("✗ 취소", width="stretch"):
            st.session_state.confirm_clear_all = False
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    💡 팁: 여러 개의 API 키를 등록하면 하나의 키가 쿼터 초과 시 자동으로 다음 키로 전환됩니다!<br>
    🔒 키는 안전하게 인코딩되어 저장되며, 활성화된 키만 사용됩니다.
</div>
""", unsafe_allow_html=True)
