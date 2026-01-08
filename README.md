# Xiaohongshu Video Downloader

Xiaohongshu(샤오홍수/小红书) 동영상을 간단하게 다운로드할 수 있는 웹 애플리케이션입니다.

## 주요 기능

- **간편한 다운로드**: URL 입력만으로 즉시 다운로드
- **일괄 처리**: 여러 개의 URL을 한 번에 다운로드
- **실시간 결과**: 다운로드 성공/실패 상태 실시간 표시
- **다크 테마 UI**: 세련된 다크 테마 인터페이스

## 기술 스택

- **Backend**: Python, FastAPI
- **Frontend**: Jinja2, Vanilla JavaScript
- **Database**: SQLite
- **Video Download**: yt-dlp

## 요구사항

- Python 3.8+
- yt-dlp (동영상 다운로드용)

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd ultracreator
```

### 2. Python 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. yt-dlp 설치

**macOS (Homebrew):**
```bash
brew install yt-dlp
```

**Linux (apt):**
```bash
sudo apt install yt-dlp
```

또는 pip으로 설치:
```bash
pip install yt-dlp
```

**Windows:**
- [yt-dlp GitHub Releases](https://github.com/yt-dlp/yt-dlp/releases)에서 다운로드
- 실행 파일을 PATH에 추가

## 실행 방법

### 방법 1: 터미널에서 실행

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

또는:

```bash
python app/main.py
```

### 방법 2: VSCode에서 실행 (추천)

1. **F5 키로 디버깅 실행**
   - VSCode에서 F5를 누르면 자동으로 서버가 실행됩니다
   - 디버깅 기능을 사용할 수 있습니다

2. **Tasks로 실행**
   - `Ctrl+Shift+P` → "Run Task" 입력
   - "Run Server" 선택

3. **단축키로 실행**
   - `Ctrl+Shift+B` (기본 빌드 작업 실행)

### 브라우저 접속

```
http://localhost:8000
```

## 사용 방법

1. **URL 입력**: Xiaohongshu 동영상 URL을 입력합니다 (여러 개 가능, 한 줄에 하나씩)
2. **다운로드 시작**: "다운로드 시작" 버튼을 클릭합니다
3. **결과 확인**: 다운로드 완료 후 파일 위치를 확인합니다

### 지원하는 URL 형식

- `https://www.xiaohongshu.com/explore/xxxxx`
- `https://xhslink.com/xxxxx`
- 기타 Xiaohongshu 동영상 URL

## 프로젝트 구조

```
ultracreator/
├── app/
│   ├── main.py                 # FastAPI 메인 앱
│   ├── db.py                   # 데이터베이스 초기화 및 연결
│   ├── api/
│   │   ├── downloader.py       # yt-dlp 다운로더
│   │   ├── downloads.py        # 다운로드 API 라우터
│   │   └── search.py           # 검색/수집 API 라우터
│   ├── models/
│   │   ├── video.py            # 비디오 모델
│   │   └── download.py         # 다운로드 모델
│   ├── templates/
│   │   ├── base.html           # 베이스 템플릿
│   │   └── index.html          # 메인 페이지
│   ├── static/
│   │   ├── css/style.css       # 스타일시트
│   │   └── js/app.js           # JavaScript 클라이언트
│   └── database.db             # SQLite 데이터베이스
├── downloads/                  # 다운로드된 영상 저장 폴더
├── requirements.txt            # Python 패키지 목록
└── README.md                   # 프로젝트 문서
```

## 다운로드 파일 위치

다운로드된 파일은 `downloads/` 폴더에 저장됩니다.

## API 엔드포인트

### 다운로드
- `POST /api/downloads/quick` - URL로 즉시 다운로드
  - Request body: `{"urls": ["url1", "url2", ...]}`
  - Response: 다운로드 결과 목록

## 주의사항

### 저작권 및 이용 약관

- **이 도구는 권한이 있는 콘텐츠만 다운로드하는 용도로 사용하세요**
- Xiaohongshu 서비스 약관을 준수하세요
- 타인의 저작권을 침해하지 마세요
- 교육, 연구, 백업 목적으로만 사용하세요

### yt-dlp 요구사항

- yt-dlp가 시스템에 설치되어 있어야 합니다
- ffmpeg가 설치되어 있으면 더 나은 품질로 다운로드할 수 있습니다

## 문제 해결

### "yt-dlp가 설치되어 있지 않습니다"

```bash
pip install yt-dlp
# 또는
brew install yt-dlp  # macOS
```

### 다운로드 실패

- 네트워크 연결을 확인하세요
- 영상이 비공개 또는 삭제되지 않았는지 확인하세요
- yt-dlp를 최신 버전으로 업데이트하세요: `pip install -U yt-dlp`
- URL 형식이 올바른지 확인하세요

### yt-dlp가 Xiaohongshu를 지원하지 않는 경우

yt-dlp는 지속적으로 업데이트되고 있습니다. 최신 버전으로 업데이트하세요:

```bash
pip install -U yt-dlp
```

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 제공됩니다. 저작권법과 Xiaohongshu 서비스 약관을 준수하여 사용하세요.

## 기여

버그 리포트나 기능 제안은 이슈로 등록해 주세요.
