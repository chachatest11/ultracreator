// ========================================
// 카테고리 관리
// ========================================

function selectCategory(categoryId) {
    currentCategoryId = categoryId;

    // 탭 활성화
    document.querySelectorAll('.category-tab').forEach(tab => {
        tab.classList.remove('active');
        if (parseInt(tab.dataset.categoryId) === categoryId) {
            tab.classList.add('active');
        }
    });

    // 채널 목록 다시 로드
    loadChannels();

    // 결과 초기화
    currentVideos = [];
    selectedVideoIds.clear();
    renderVideoGrid();
    updateResultInfo();
}

function openCategoryModal() {
    loadCategories();
    document.getElementById('categoryModal').classList.add('active');
}

function closeCategoryModal() {
    document.getElementById('categoryModal').classList.remove('active');
}

async function loadCategories() {
    try {
        const response = await fetch('/api/categories/');
        const data = await response.json();

        const categoryList = document.getElementById('categoryList');
        categoryList.innerHTML = '';

        data.categories.forEach(category => {
            const item = document.createElement('div');
            item.className = 'category-item';
            item.innerHTML = `
                <span class="category-item-name">${category.name}</span>
                <div class="category-item-actions">
                    ${category.id !== 1 ? `
                        <button class="btn-edit" onclick="editCategory(${category.id}, '${category.name}')">수정</button>
                        <button class="btn-delete" onclick="deleteCategory(${category.id})">삭제</button>
                    ` : ''}
                </div>
            `;
            categoryList.appendChild(item);
        });
    } catch (error) {
        console.error('카테고리 로드 실패:', error);
        alert('카테고리를 불러오는데 실패했습니다.');
    }
}

async function addCategory() {
    const nameInput = document.getElementById('newCategoryName');
    const name = nameInput.value.trim();

    if (!name) {
        alert('카테고리 이름을 입력하세요.');
        return;
    }

    try {
        const response = await fetch('/api/categories/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        if (response.ok) {
            nameInput.value = '';
            loadCategories();
            location.reload(); // 탭 갱신
        } else {
            const error = await response.json();
            alert(error.detail || '카테고리 추가 실패');
        }
    } catch (error) {
        console.error('카테고리 추가 실패:', error);
        alert('카테고리 추가에 실패했습니다.');
    }
}

async function editCategory(id, currentName) {
    const newName = prompt('새 카테고리 이름:', currentName);
    if (!newName || newName === currentName) return;

    try {
        const response = await fetch(`/api/categories/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });

        if (response.ok) {
            loadCategories();
            location.reload(); // 탭 갱신
        } else {
            const error = await response.json();
            alert(error.detail || '카테고리 수정 실패');
        }
    } catch (error) {
        console.error('카테고리 수정 실패:', error);
        alert('카테고리 수정에 실패했습니다.');
    }
}

async function deleteCategory(id) {
    if (!confirm('이 카테고리를 삭제하시겠습니까?\n(채널은 기본 카테고리로 이동됩니다)')) {
        return;
    }

    try {
        const response = await fetch(`/api/categories/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadCategories();
            location.reload(); // 탭 갱신
        } else {
            const error = await response.json();
            alert(error.detail || '카테고리 삭제 실패');
        }
    } catch (error) {
        console.error('카테고리 삭제 실패:', error);
        alert('카테고리 삭제에 실패했습니다.');
    }
}

// ========================================
// 채널 관리
// ========================================

async function loadChannels() {
    try {
        const response = await fetch(`/api/channels/?category_id=${currentCategoryId}`);
        const data = await response.json();

        const channelsList = document.getElementById('channelsList');
        channelsList.innerHTML = '';

        if (data.channels.length === 0) {
            channelsList.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">등록된 채널이 없습니다. 채널을 추가하세요.</p>';
            return;
        }

        data.channels.forEach(channel => {
            const card = document.createElement('div');
            card.className = `channel-card ${channel.is_active ? '' : 'inactive'}`;
            card.innerHTML = `
                <div class="channel-info">
                    <div class="channel-title">
                        ${escapeHtml(channel.title || channel.channel_id)}
                        <a href="https://www.youtube.com/channel/${channel.channel_id}"
                           target="_blank"
                           class="channel-link"
                           title="채널 보기">🔗</a>
                    </div>
                    <div class="channel-meta">
                        구독자 ${formatSubscriberCount(channel.subscriber_count || 0)}
                        ${channel.country ? `· ${channel.country}` : ''}
                    </div>
                </div>
                <div class="channel-actions">
                    <button class="btn-refresh-channel" onclick="refreshChannelInfo(${channel.id})" title="채널 정보 새로고침">🔄</button>
                    <label class="toggle-switch">
                        <input type="checkbox"
                               ${channel.is_active ? 'checked' : ''}
                               onchange="toggleChannelActive(${channel.id})">
                        <span class="toggle-slider"></span>
                    </label>
                    <button class="btn-delete-channel" onclick="deleteChannel(${channel.id})">삭제</button>
                </div>
            `;
            channelsList.appendChild(card);
        });
    } catch (error) {
        console.error('채널 로드 실패:', error);
    }
}

function openAddChannelModal() {
    document.getElementById('addChannelModal').classList.add('active');
    // 기본적으로 수동 입력 탭 표시
    switchUploadTab('manual');
}

function closeAddChannelModal() {
    document.getElementById('addChannelModal').classList.remove('active');
    document.getElementById('channelInput').value = '';
    document.getElementById('mdFileInput').value = '';
    document.getElementById('filePreview').style.display = 'none';
}

function switchUploadTab(tabName) {
    // 탭 버튼 활성화
    document.querySelectorAll('.upload-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event?.target?.classList.add('active') ||
        document.querySelector(`.upload-tab:${tabName === 'manual' ? 'first' : 'last'}-child`)?.classList.add('active');

    // 탭 콘텐츠 표시
    document.getElementById('manualInputTab').classList.remove('active');
    document.getElementById('fileUploadTab').classList.remove('active');

    if (tabName === 'manual') {
        document.getElementById('manualInputTab').classList.add('active');
    } else {
        document.getElementById('fileUploadTab').classList.add('active');
    }
}

async function addChannels() {
    const apiKeyInput = document.getElementById('apiKey');
    apiKey = apiKeyInput.value.trim();

    if (!apiKey) {
        alert('YouTube API Key를 입력하세요.');
        apiKeyInput.focus();
        closeAddChannelModal();
        return;
    }

    saveApiKey(apiKey);

    const channelInput = document.getElementById('channelInput').value.trim();
    const channelInputs = channelInput
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);

    if (channelInputs.length === 0) {
        alert('채널을 입력하세요.');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch('/api/channels/bulk_upsert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category_id: currentCategoryId,
                channel_inputs: channelInputs,
                api_key: apiKey
            })
        });

        const result = await response.json();

        if (result.success > 0) {
            alert(`${result.success}개 채널이 추가되었습니다.${result.failed > 0 ? `\n실패: ${result.failed}개` : ''}`);
            closeAddChannelModal();
            loadChannels();
        } else {
            alert('채널 추가에 실패했습니다.\n' + (result.errors || []).map(e => e.error).join('\n'));
        }
    } catch (error) {
        console.error('채널 추가 실패:', error);
        alert('채널 추가에 실패했습니다.');
    } finally {
        showLoading(false);
    }
}

async function toggleChannelActive(channelId) {
    try {
        const response = await fetch(`/api/channels/${channelId}/toggle_active`, {
            method: 'PUT'
        });

        if (response.ok) {
            loadChannels();
        } else {
            alert('채널 상태 변경에 실패했습니다.');
        }
    } catch (error) {
        console.error('채널 상태 변경 실패:', error);
        alert('채널 상태 변경에 실패했습니다.');
    }
}

async function deleteChannel(channelId) {
    if (!confirm('이 채널을 삭제하시겠습니까?')) {
        return;
    }

    try {
        const response = await fetch(`/api/channels/${channelId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadChannels();
        } else {
            alert('채널 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('채널 삭제 실패:', error);
        alert('채널 삭제에 실패했습니다.');
    }
}

async function refreshChannelInfo(channelId) {
    const apiKeyInput = document.getElementById('apiKey');
    const apiKey = apiKeyInput.value.trim();

    if (!apiKey) {
        alert('YouTube API Key를 입력하세요.');
        apiKeyInput.focus();
        return;
    }

    try {
        const response = await fetch(`/api/channels/${channelId}/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });

        if (response.ok) {
            const result = await response.json();
            alert(`채널 정보가 업데이트되었습니다.\n\n제목: ${result.title}\n구독자: ${formatSubscriberCount(result.subscriber_count)}`);
            loadChannels();
        } else {
            const error = await response.json();
            alert(error.detail || '채널 정보 업데이트 실패');
        }
    } catch (error) {
        console.error('채널 정보 업데이트 실패:', error);
        alert('채널 정보 업데이트에 실패했습니다.');
    }
}

async function uploadMdFile() {
    const apiKeyInput = document.getElementById('apiKey');
    apiKey = apiKeyInput.value.trim();

    if (!apiKey) {
        alert('YouTube API Key를 입력하세요.');
        apiKeyInput.focus();
        return;
    }

    const fileInput = document.getElementById('mdFileInput');
    const file = fileInput.files[0];

    if (!file) {
        alert('파일을 선택하세요.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category_id', currentCategoryId);
    formData.append('api_key', apiKey);

    showLoading(true);

    try {
        const response = await fetch('/api/channels/upload_md', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success > 0) {
            alert(`${result.success}개 채널이 추가되었습니다.${result.failed > 0 ? `\n실패: ${result.failed}개` : ''}\n\n발견된 URL: ${result.urls_found}개`);
            closeAddChannelModal();
            loadChannels();
        } else {
            alert('채널 추가에 실패했습니다.\n' + (result.errors || []).map(e => e.error).join('\n'));
        }
    } catch (error) {
        console.error('파일 업로드 실패:', error);
        alert('파일 업로드에 실패했습니다.');
    } finally {
        showLoading(false);
    }
}

// MD 파일 선택 시 미리보기
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('mdFileInput');
    if (fileInput) {
        fileInput.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;

            const text = await file.text();
            const urls = extractYouTubeUrls(text);

            const preview = document.getElementById('filePreview');
            const urlList = document.getElementById('urlList');

            if (urls.length > 0) {
                urlList.innerHTML = urls.map(url =>
                    `<div style="font-size: 11px; color: #2196f3; padding: 4px 0; border-bottom: 1px solid #1a1a1a;">${escapeHtml(url)}</div>`
                ).join('');
                preview.style.display = 'block';
            } else {
                preview.style.display = 'none';
                alert('파일에서 YouTube URL을 찾을 수 없습니다.');
            }
        });
    }
});

function extractYouTubeUrls(text) {
    const patterns = [
        /https?:\/\/(?:www\.)?youtube\.com\/channel\/([a-zA-Z0-9_-]+)/g,
        /https?:\/\/(?:www\.)?youtube\.com\/@([a-zA-Z0-9_-]+)/g,
        /https?:\/\/(?:www\.)?youtube\.com\/c\/([a-zA-Z0-9_-]+)/g,
        /https?:\/\/(?:www\.)?youtube\.com\/user\/([a-zA-Z0-9_-]+)/g,
    ];

    const urls = new Set();
    patterns.forEach(pattern => {
        const matches = text.matchAll(pattern);
        for (const match of matches) {
            urls.add(match[0]);
        }
    });

    return Array.from(urls);
}

// ========================================
// 검색 및 영상 수집
// ========================================

async function searchVideos() {
    // API Key 확인
    const apiKeyInput = document.getElementById('apiKey');
    apiKey = apiKeyInput.value.trim();

    if (!apiKey) {
        alert('YouTube API Key를 입력하세요.');
        apiKeyInput.focus();
        return;
    }

    // API Key 저장
    saveApiKey(apiKey);

    const maxVideos = parseInt(document.getElementById('maxVideos').value) || 50;

    // 로딩 시작
    showLoading(true);

    try {
        // DB에 저장된 활성 채널들로부터 영상 검색
        const searchResponse = await fetch('/api/search/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category_id: currentCategoryId,
                api_key: apiKey,
                max_videos: maxVideos,
                min_views_man: parseInt(document.getElementById('minViews').value) || 0,
                sort: document.getElementById('sortBy').value
            })
        });

        const searchResult = await searchResponse.json();

        if (!searchResponse.ok) {
            throw new Error(searchResult.detail || '검색 실패');
        }

        currentVideos = searchResult.videos || [];

        // 결과 표시
        renderVideoGrid();
        updateResultInfo();

        // 결과 옵션 표시
        document.getElementById('resultOptions').style.display = 'flex';

        if (searchResult.errors && searchResult.errors.length > 0) {
            console.warn('일부 채널에서 오류 발생:', searchResult.errors);
        }

        if (currentVideos.length === 0) {
            alert('검색 결과가 없습니다.\n활성화된 채널이 있는지 확인하세요.');
        }

    } catch (error) {
        console.error('검색 실패:', error);
        alert('검색에 실패했습니다.\n' + error.message);
    } finally {
        showLoading(false);
    }
}

async function applyFilters() {
    showLoading(true);

    try {
        const response = await fetch(
            `/api/search/videos?category_id=${currentCategoryId}` +
            `&min_views_man=${parseInt(document.getElementById('minViews').value) || 0}` +
            `&sort=${document.getElementById('sortBy').value}`
        );

        const data = await response.json();
        currentVideos = data.videos || [];

        renderVideoGrid();
        updateResultInfo();

    } catch (error) {
        console.error('필터 적용 실패:', error);
    } finally {
        showLoading(false);
    }
}

// ========================================
// 비디오 그리드 렌더링
// ========================================

function renderVideoGrid() {
    const grid = document.getElementById('videoGrid');

    if (currentVideos.length === 0) {
        grid.innerHTML = '<p class="text-center" style="grid-column: 1 / -1; color: #999;">검색 결과가 없습니다.</p>';
        return;
    }

    grid.innerHTML = '';

    currentVideos.forEach(video => {
        const card = createVideoCard(video);
        grid.appendChild(card);
    });
}

function createVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'video-card';
    card.dataset.videoId = video.video_id;

    if (selectedVideoIds.has(video.video_id)) {
        card.classList.add('selected');
    }

    // 조회수 포맷팅
    const viewCount = formatViewCount(video.view_count);

    // 날짜 포맷팅
    const publishedDate = formatDate(video.published_at);

    card.innerHTML = `
        <div class="video-thumbnail" onclick="openYouTube('${video.video_id}')">
            <img src="${video.thumbnail_url}" alt="${video.title}" loading="lazy">
        </div>
        <div class="video-info">
            <div class="video-title">${escapeHtml(video.title)}</div>
            <div class="video-meta">
                <span>조회수 ${viewCount}</span>
                <span>${escapeHtml(video.channel_title || '')}</span>
                <span>${publishedDate}</span>
            </div>
        </div>
        <div class="video-toggle">
            <div class="toggle-checkbox">
                <input type="checkbox" id="toggle-${video.video_id}"
                       ${selectedVideoIds.has(video.video_id) ? 'checked' : ''}
                       onchange="toggleVideoSelection('${video.video_id}')">
                <label for="toggle-${video.video_id}">영상추출</label>
            </div>
        </div>
    `;

    return card;
}

function toggleVideoSelection(videoId) {
    if (selectedVideoIds.has(videoId)) {
        selectedVideoIds.delete(videoId);
    } else {
        selectedVideoIds.add(videoId);
    }

    // 카드 스타일 업데이트
    const card = document.querySelector(`[data-video-id="${videoId}"]`);
    if (card) {
        card.classList.toggle('selected');
    }

    updateResultInfo();
}

function updateResultInfo() {
    document.getElementById('resultCount').textContent = `${currentVideos.length}개 영상`;

    const selectedCountEl = document.getElementById('selectedCount');
    const downloadBtn = document.getElementById('btnDownload');

    if (selectedVideoIds.size > 0) {
        selectedCountEl.textContent = `${selectedVideoIds.size}개 선택`;
        selectedCountEl.style.display = 'block';
        downloadBtn.style.display = 'block';
    } else {
        selectedCountEl.style.display = 'none';
        downloadBtn.style.display = 'none';
    }
}

// ========================================
// 다운로드
// ========================================

async function downloadSelected() {
    if (selectedVideoIds.size === 0) {
        alert('다운로드할 영상을 선택하세요.');
        return;
    }

    const videoIds = Array.from(selectedVideoIds);
    const modal = document.getElementById('downloadModal');
    const statusEl = document.getElementById('downloadStatus');
    const progressFill = document.getElementById('progressFill');
    const resultsEl = document.getElementById('downloadResults');

    // 모달 열기
    modal.classList.add('active');
    statusEl.textContent = '다운로드 시작 중...';
    progressFill.style.width = '0%';
    resultsEl.innerHTML = '';

    try {
        const response = await fetch('/api/downloads/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_ids: videoIds })
        });

        const result = await response.json();

        // 진행률 업데이트
        const successRate = (result.success / result.total) * 100;
        progressFill.style.width = '100%';
        statusEl.textContent = `완료: ${result.success}개 / 실패: ${result.failed}개`;

        // 결과 표시
        result.results.forEach(item => {
            const resultItem = document.createElement('div');
            resultItem.className = `download-result-item ${item.status}`;
            resultItem.innerHTML = `
                <strong>${escapeHtml(item.video_title || item.video_id)}</strong><br>
                ${item.status === 'done' ? '✓ 다운로드 완료' : `✗ 실패: ${item.error}`}
            `;
            resultsEl.appendChild(resultItem);
        });

        // 3초 후 자동 닫기 (성공 시)
        if (result.failed === 0) {
            setTimeout(() => {
                modal.classList.remove('active');
            }, 3000);
        }

    } catch (error) {
        console.error('다운로드 실패:', error);
        statusEl.textContent = '다운로드 중 오류가 발생했습니다.';
        alert('다운로드에 실패했습니다.');
    }
}

// ========================================
// API Key 관리
// ========================================

function openApiKeyModal() {
    loadApiKeys();
    document.getElementById('apiKeyModal').classList.add('active');
}

function closeApiKeyModal() {
    document.getElementById('apiKeyModal').classList.remove('active');
}

async function loadApiKeys() {
    try {
        const response = await fetch('/api/api_keys/');
        const data = await response.json();

        const apiKeyList = document.getElementById('apiKeyList');
        apiKeyList.innerHTML = '';

        if (data.api_keys.length === 0) {
            apiKeyList.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">등록된 API 키가 없습니다.</p>';
            return;
        }

        data.api_keys.forEach(apiKey => {
            const item = document.createElement('div');
            item.className = 'category-item';

            // 날짜 포맷팅
            const createdDate = new Date(apiKey.created_at).toLocaleDateString('ko-KR');

            // 상태 표시
            let statusBadge = '';
            if (apiKey.quota_exceeded) {
                statusBadge = '<span style="color: #f44336; font-size: 12px; margin-left: 8px;">⚠ 쿼터 초과</span>';
            } else if (!apiKey.is_active) {
                statusBadge = '<span style="color: #999; font-size: 12px; margin-left: 8px;">비활성</span>';
            } else {
                statusBadge = '<span style="color: #4caf50; font-size: 12px; margin-left: 8px;">✓ 활성</span>';
            }

            item.innerHTML = `
                <div>
                    <div class="category-item-name">
                        ${apiKey.api_key}
                        ${statusBadge}
                    </div>
                    <div style="font-size: 11px; color: #666; margin-top: 4px;">
                        ${apiKey.name ? apiKey.name + ' · ' : ''}${createdDate}
                        ${apiKey.last_used_at ? ' · 마지막 사용: ' + formatDate(apiKey.last_used_at) : ''}
                    </div>
                </div>
                <div class="category-item-actions">
                    ${apiKey.quota_exceeded ? `
                        <button class="btn-edit" onclick="resetQuota(${apiKey.id})">쿼터 초기화</button>
                    ` : ''}
                    <button class="btn-delete" onclick="deleteApiKey(${apiKey.id})">삭제</button>
                </div>
            `;
            apiKeyList.appendChild(item);
        });
    } catch (error) {
        console.error('API 키 로드 실패:', error);
        alert('API 키를 불러오는데 실패했습니다.');
    }
}

async function addApiKey() {
    const keyInput = document.getElementById('newApiKey');
    const nameInput = document.getElementById('newApiKeyName');
    const key = keyInput.value.trim();
    const name = nameInput.value.trim();

    if (!key) {
        alert('API 키를 입력하세요.');
        return;
    }

    try {
        const response = await fetch('/api/api_keys/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: key,
                name: name || null,
                priority: 0
            })
        });

        if (response.ok) {
            keyInput.value = '';
            nameInput.value = '';
            loadApiKeys();

            // 첫 번째 API 키라면 자동으로 입력란에 설정
            const data = await response.json();
            if (!apiKey) {
                document.getElementById('apiKey').value = key;
                apiKey = key;
            }
        } else {
            const error = await response.json();
            alert(error.detail || 'API 키 추가 실패');
        }
    } catch (error) {
        console.error('API 키 추가 실패:', error);
        alert('API 키 추가에 실패했습니다.');
    }
}

async function deleteApiKey(id) {
    if (!confirm('이 API 키를 삭제하시겠습니까?')) {
        return;
    }

    try {
        const response = await fetch(`/api/api_keys/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadApiKeys();
        } else {
            const error = await response.json();
            alert(error.detail || 'API 키 삭제 실패');
        }
    } catch (error) {
        console.error('API 키 삭제 실패:', error);
        alert('API 키 삭제에 실패했습니다.');
    }
}

async function resetQuota(id) {
    try {
        const response = await fetch(`/api/api_keys/${id}/reset_quota`, {
            method: 'POST'
        });

        if (response.ok) {
            loadApiKeys();
            alert('쿼터가 초기화되었습니다.');
        } else {
            const error = await response.json();
            alert(error.detail || '쿼터 초기화 실패');
        }
    } catch (error) {
        console.error('쿼터 초기화 실패:', error);
        alert('쿼터 초기화에 실패했습니다.');
    }
}

async function loadApiKey() {
    try {
        const response = await fetch('/api/api_keys/active');
        const data = await response.json();

        if (data.api_key && data.api_key.api_key) {
            document.getElementById('apiKey').value = data.api_key.api_key;
            apiKey = data.api_key.api_key;
        }
    } catch (error) {
        console.error('API Key 로드 실패:', error);
        // 사용 가능한 API 키가 없어도 무시
    }
}

async function saveApiKey(key) {
    // 이 함수는 더 이상 사용되지 않음 (DB에 직접 저장하므로)
    // 하지만 기존 코드와의 호환성을 위해 남겨둠
}

// ========================================
// 유틸리티
// ========================================

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

function openYouTube(videoId) {
    window.open(`https://www.youtube.com/watch?v=${videoId}`, '_blank');
}

function formatViewCount(count) {
    if (count >= 100000000) {
        return `${(count / 100000000).toFixed(1)}억`;
    } else if (count >= 10000) {
        return `${(count / 10000).toFixed(1)}만`;
    } else if (count >= 1000) {
        return `${(count / 1000).toFixed(1)}천`;
    } else {
        return count.toString();
    }
}

function formatSubscriberCount(count) {
    if (count >= 10000000) {
        return `${(count / 10000000).toFixed(0)}천만`;
    } else if (count >= 10000) {
        return `${(count / 10000).toFixed(1)}만`;
    } else if (count >= 1000) {
        return `${(count / 1000).toFixed(1)}천`;
    } else {
        return count.toString();
    }
}

function formatDate(dateString) {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const months = Math.floor(days / 30);
    const years = Math.floor(days / 365);

    if (years > 0) return `${years}년 전`;
    if (months > 0) return `${months}개월 전`;
    if (days > 0) return `${days}일 전`;
    if (hours > 0) return `${hours}시간 전`;
    if (minutes > 0) return `${minutes}분 전`;
    return '방금 전';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 모달 외부 클릭 시 닫기
window.addEventListener('click', function(event) {
    const categoryModal = document.getElementById('categoryModal');
    const apiKeyModal = document.getElementById('apiKeyModal');
    const downloadModal = document.getElementById('downloadModal');

    if (event.target === categoryModal) {
        closeCategoryModal();
    }

    if (event.target === apiKeyModal) {
        closeApiKeyModal();
    }

    // 다운로드 모달은 외부 클릭으로 안 닫히게
});
