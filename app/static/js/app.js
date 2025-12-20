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
                    <div class="channel-title">${escapeHtml(channel.title || channel.channel_id)}</div>
                    <div class="channel-meta">
                        구독자 ${formatSubscriberCount(channel.subscriber_count || 0)}
                        ${channel.country ? `· ${channel.country}` : ''}
                    </div>
                </div>
                <div class="channel-actions">
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
}

function closeAddChannelModal() {
    document.getElementById('addChannelModal').classList.remove('active');
    document.getElementById('channelInput').value = '';
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

    localStorage.setItem('youtube_api_key', apiKey);

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
    localStorage.setItem('youtube_api_key', apiKey);

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
    const downloadModal = document.getElementById('downloadModal');

    if (event.target === categoryModal) {
        closeCategoryModal();
    }

    // 다운로드 모달은 외부 클릭으로 안 닫히게
});
