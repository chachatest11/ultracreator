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

### 🌐 Keyword Explorer
- YouTube 카테고리별 트렌딩 키워드 수집
- 7개 언어 자동 번역 (한국어, 영어, 일본어, 중국어, 스페인어, 힌디어, 러시아어)
- Google Trends 기반 실시간 데이터
- DeepL/Google Translate 번역 지원
- 24시간 캐싱으로 빠른 재조회

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

#### Option 1: 단일 API 키 (기본)

```bash
YOUTUBE_API_KEY=your_api_key_here
```

#### Option 2: 여러 API 키 (권장 🌟)

여러 개의 API 키를 사용하면 하나의 키가 쿼터 초과 시 자동으로 다음 키로 전환됩니다!

```bash
YOUTUBE_API_KEYS=key1,key2,key3,key4,key5
```

**예시:**
```bash
YOUTUBE_API_KEYS=AIzaSyXXXXXXXXXXXXXXX1,AIzaSyXXXXXXXXXXXXXXX2,AIzaSyXXXXXXXXXXXXXXX3
```

**장점:**
- ✅ 하루 쿼터를 키 개수만큼 늘릴 수 있음 (키 3개 = 30,000 유닛)
- ✅ 자동 키 전환으로 중단 없이 계속 사용 가능
- ✅ 키 상태를 터미널에서 실시간 확인

**중요:** `.env` 파일에 실제 API 키를 입력하세요.

#### Option 3: DeepL API 키 (선택사항, 키워드 탐색 기능용)

키워드 번역 기능에서 더 높은 품질의 번역을 사용하려면:

```bash
DEEPL_API_KEY=your_deepl_api_key_here
```

- 무료 계정: https://www.deepl.com/pro-api (월 50만 글자 무료)
- 설정하지 않으면 Google Translate (무료)가 자동으로 사용됩니다

#### Option 4: UI에서 관리 (가장 편리! 🎯)

앱을 실행한 후 **API Key Manager** 페이지에서 키를 추가/삭제/관리할 수 있습니다!

**장점:**
- ✅ 앱 재시작 없이 즉시 키 추가/삭제
- ✅ 키별 이름 설정 및 활성화/비활성화
- ✅ 키 상태 및 사용 내역 확인
- ✅ 일괄 가져오기 기능으로 빠른 설정
- ✅ .env 파일 수정 불필요

**사용 방법:**
1. 앱 실행: `streamlit run app.py`
2. 왼쪽 사이드바에서 **🔑 API Key Manager** 페이지 선택
3. 키 추가/관리

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

### 키워드 탐색

1. **Keyword Explorer** 페이지 이동
2. YouTube 카테고리 선택:
   - 게임, 스포츠, 음악, 영화/애니메이션 등 12개 카테고리
3. (선택사항) 커스텀 키워드 입력
4. "🔎 검색" 버튼 클릭
5. 결과 확인:
   - 7개 언어로 번역된 트렌딩 키워드 목록
   - CSV로 다운로드하여 활용
   - 24시간 동안 결과가 캐싱됨

**참고:** 이 기능을 사용하려면 다음 패키지 설치가 필요합니다:
```bash
pip install pytrends deepl deep-translator
```

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
│   ├── 1_📊_채널_목록.py        # 채널 목록/대시보드
│   ├── 2_📈_상세_분석.py        # 채널 상세 분석
│   ├── 3_⭐_그룹_관리.py        # 워치리스트
│   ├── 4_🎯_트렌드_분석.py      # 니치 탐색
│   ├── 5_🔑_API_키_관리.py     # API 키 관리
│   └── 6_🌐_키워드_탐색.py      # 키워드 탐색 (NEW!)
├── core/
│   ├── youtube_api.py          # YouTube API 클라이언트
│   ├── db.py                   # 데이터베이스 작업
│   ├── models.py               # 데이터 모델
│   ├── metrics.py              # 지표 계산
│   ├── niche.py                # 니치 탐색 엔진
│   ├── trends.py               # 트렌드 & 번역 (NEW!)
│   ├── jobs.py                 # 데이터 수집 작업
│   └── api_key_storage.py      # API 키 저장소
├── requirements.txt            # Python 의존성
├── .env                        # 환경 변수 (직접 생성)
├── .env.example                # 환경 변수 예시
├── db.sqlite                   # SQLite 데이터베이스 (자동 생성)
└── README.md                   # 이 파일
```

## 문제 해결

### API 키 오류
```
YouTube API key not found
```
→ `.env` 파일에 `YOUTUBE_API_KEY` 또는 `YOUTUBE_API_KEYS`가 설정되었는지 확인

### 쿼터 초과 🔥

```
quotaExceeded
```

YouTube API는 **일일 쿼터 제한**이 있습니다 (기본 10,000 유닛/일)

#### 해결책:

**1. 여러 API 키 사용 (권장 ⭐)**
```bash
# .env 파일에 여러 키 추가
YOUTUBE_API_KEYS=key1,key2,key3,key4,key5
```
- 키가 5개라면 → **50,000 유닛/일** 사용 가능!
- 하나의 키가 초과되면 자동으로 다음 키로 전환
- 터미널에서 전환 상태 실시간 확인:
  ```
  ⚠️  API Key #1 quota exceeded. Switching to next key...
  📍 Switched from Key #1 to Key #2
  ✅ Available keys: 4/5
  ```

**2. 다음날까지 대기**

**3. Google Cloud에서 쿼터 증가 요청**

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

### 키워드 탐색 기능 오류
```
ModuleNotFoundError: No module named 'pytrends'
```
→ 키워드 탐색 기능을 사용하려면 추가 패키지 설치가 필요합니다:
```bash
pip install pytrends deepl deep-translator
```
또는 전체 의존성을 다시 설치:
```bash
pip install -r requirements.txt
```

## 확장 포인트 (TODO)

- [x] 다국어 키워드 탐색 (완료!)
- [x] API 키 UI 관리 (완료!)
- [ ] OAuth 2.0 인증 추가 (개인 채널 상세 정보)
- [ ] 댓글 분석 기능
- [ ] 태그/카테고리 분석
- [ ] 자동 리포트 생성 (PDF/Excel)
- [ ] 알림 설정 (특정 조건 달성 시)
- [ ] 더 많은 영상 수집 (페이지네이션 개선)

## 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: SQLite
- **API**:
  - YouTube Data API v3
  - DeepL Translation API (optional)
- **ML/NLP**: sentence-transformers, scikit-learn
- **Trends**: pytrends (Google Trends)
- **Translation**: DeepL, Google Translate (deep-translator)
- **Visualization**: Plotly

## 라이선스

MIT License

## 지원

문제가 발생하면 GitHub Issues에 보고해주세요.

---

Made with ❤️ for YouTube Shorts Researchers
