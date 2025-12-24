# NexLev Mini - YouTube Analytics Dashboard

YouTube 채널 분석 및 니치 탐색 도구 (해외 양산형 쇼츠 리서치)

## 기능

### 📈 Dashboard
- 관심 채널 추가/삭제/갱신
- 주요 지표 모니터링 (구독자, 조회수, 성장률)
- Shorts 중심 필터링
- 업로드 패턴 분석

### 🔍 Channel Detail
- 채널 상세 분석
- 최근 50개 영상 데이터
- 조회수 분포 시각화
- 업로드 패턴 (요일/시간대)

### 📋 Watchlists
- 워치리스트 생성/관리
- 채널 그룹화 및 비교
- 성과 랭킹
- 패턴 분석

### 🎯 Niche Explorer
- 키워드 기반 영상 수집 (200~500개)
- AI 임베딩 + 클러스터링
- 니치 점수화 (성과/경쟁/집중도)
- 진입 가능성 분석

## 시작하기

### 1. 사전 요구사항

- Python 3.8 이상
- YouTube Data API v3 키

### 2. YouTube API 키 발급

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성
3. "API 및 서비스" > "라이브러리" 이동
4. "YouTube Data API v3" 검색 및 활성화
5. "사용자 인증 정보" > "사용자 인증 정보 만들기" > "API 키" 선택
6. API 키 복사

### 3. 설치

```bash
# 저장소 클론 또는 다운로드
cd ultracreator

# 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 4. 환경 설정

`.env` 파일을 프로젝트 루트에 생성:

```bash
YOUTUBE_API_KEY=your_api_key_here
```

**중요:** `.env` 파일에 실제 API 키를 입력하세요.

### 5. 실행

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501`에서 앱이 실행됩니다.

## 사용 방법

### 채널 추가

1. **Dashboard** 페이지로 이동
2. 사이드바에서 채널 정보 입력:
   - 채널 ID: `UC1234567890abcdefghijk`
   - 핸들: `@username`
   - URL: `https://youtube.com/@username`
3. "채널 추가" 버튼 클릭

### 채널 분석

1. **Dashboard**에서 채널 선택
2. "📊 상세 보기" 클릭 또는 **Channel Detail** 페이지 이동
3. 주요 지표 확인:
   - 구독자/조회수/성장률
   - 업로드 주기/패턴
   - Shorts 비중
   - 조회수 분산 (안정형/한방형)

### 워치리스트 활용

1. **Watchlists** 페이지 이동
2. 사이드바에서 새 워치리스트 생성
3. 채널 추가/제거
4. 비교 테이블 및 차트로 성과 분석

### 니치 탐색

1. **Niche Explorer** 페이지 이동
2. 키워드 입력 (예: "cute animals", "cooking shorts")
3. 설정 조정:
   - 최대 영상 수: 200~300 권장
   - 클러스터 수: 6~10 권장
4. "🚀 탐색 시작" 클릭
5. 결과 분석:
   - 종합 점수가 높은 클러스터 확인
   - 대표 영상/채널 참고
   - 발견한 채널을 Dashboard에 추가

## 주요 지표 설명

### 업로드 주기
최근 20개 영상의 업로드 간격 평균/중앙값 (일 단위)

### 조회수 분산 (CV)
- **안정형 (CV < 0.5)**: 조회수가 일정하게 유지
- **한방형 (CV ≥ 0.5)**: 특정 영상에 조회수 집중

### Shorts 비중
최근 50개 영상 중 60초 이하 영상의 비율

### Top5 집중도
최근 50개 영상 중 상위 5개 영상이 차지하는 조회수 비율

### 니치 종합 점수
```
종합 점수 = 성과 - 0.7×경쟁 - 0.5×집중도
```
- **성과**: log(중앙 조회수 + 1)
- **경쟁**: log(고유 채널 수 + 1)
- **집중도**: Top10 조회수 비중

점수가 높을수록 진입하기 좋은 니치입니다.

## 폴더 구조

```
ultracreator/
├── app.py                      # 메인 진입점
├── pages/
│   ├── 1_Dashboard.py          # 대시보드
│   ├── 2_Channel_Detail.py     # 채널 상세
│   ├── 3_Watchlists.py         # 워치리스트
│   └── 4_Niche_Explorer.py     # 니치 탐색
├── core/
│   ├── youtube_api.py          # YouTube API 클라이언트
│   ├── db.py                   # 데이터베이스 작업
│   ├── models.py               # 데이터 모델
│   ├── metrics.py              # 지표 계산
│   ├── niche.py                # 니치 탐색 엔진
│   └── jobs.py                 # 데이터 수집 작업
├── requirements.txt            # Python 의존성
├── .env                        # 환경 변수 (직접 생성)
├── db.sqlite                   # SQLite 데이터베이스 (자동 생성)
└── README.md                   # 이 파일
```

## 문제 해결

### API 키 오류
```
YouTube API key not found
```
→ `.env` 파일에 `YOUTUBE_API_KEY`가 설정되었는지 확인

### 쿼터 초과
```
quotaExceeded
```
→ YouTube API는 일일 쿼터 제한이 있습니다 (기본 10,000 유닛)
→ 다음날까지 대기하거나 Google Cloud에서 쿼터 증가 요청

### 채널을 찾을 수 없음
```
Channel not found
```
→ 채널 ID/핸들/URL이 정확한지 확인
→ 비공개 채널은 검색되지 않습니다

### 느린 성능
- 니치 탐색에서 영상 수를 줄이세요 (100~200개)
- 클러스터 수를 줄이세요 (5~8개)
- 캐시 사용 옵션을 활성화하세요

## 확장 포인트 (TODO)

- [ ] OAuth 2.0 인증 추가 (개인 채널 상세 정보)
- [ ] 댓글 분석 기능
- [ ] 태그/카테고리 분석
- [ ] 자동 리포트 생성 (PDF/Excel)
- [ ] 알림 설정 (특정 조건 달성 시)
- [ ] 더 많은 영상 수집 (페이지네이션 개선)
- [ ] 다국어 지원

## 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: SQLite
- **API**: YouTube Data API v3
- **ML/NLP**: sentence-transformers, scikit-learn
- **Visualization**: Plotly

## 라이선스

MIT License

## 지원

문제가 발생하면 GitHub Issues에 보고해주세요.

---

Made with ❤️ for YouTube Shorts Researchers
