# 로컬 실행 가이드

## 1. 가상환경 활성화

### macOS/Linux
```bash
source venv/bin/activate
```

### Windows
```bash
venv\Scripts\activate
```

활성화되면 터미널 프롬프트 앞에 `(venv)`가 표시됩니다.

## 2. 패키지 설치 (최초 1회만)
```bash
pip install -r requirements.txt
```

## 3. 서버 실행
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

또는
```bash
cd app
python main.py
```

## 4. 브라우저 접속
```
http://localhost:8000
```

## 5. 사용 완료 후 가상환경 비활성화
```bash
deactivate
```

---

## 전체 실행 예시 (처음 시작할 때)

```bash
# 1. 프로젝트 폴더로 이동
cd shortscrwal

# 2. 가상환경 활성화
source venv/bin/activate

# 3. 패키지 설치 (최초 1회만)
pip install -r requirements.txt

# 4. 서버 실행
python -m uvicorn app.main:app --reload

# 5. 브라우저에서 http://localhost:8000 접속
```

## 두 번째 실행부터는

```bash
# 1. 프로젝트 폴더로 이동
cd shortscrwal

# 2. 가상환경 활성화
source venv/bin/activate

# 3. 서버 실행
python -m uvicorn app.main:app --reload
```

---

## yt-dlp 설치 (다운로드 기능 사용 시)

### macOS
```bash
brew install yt-dlp
```

### 또는 pip로 (가상환경 활성화 후)
```bash
pip install yt-dlp
```

---

## 문제 해결

### "command not found: python"
```bash
# python3로 실행
python3 -m uvicorn app.main:app --reload
```

### 포트가 이미 사용 중일 때
```bash
# 다른 포트 사용 (예: 8001)
python -m uvicorn app.main:app --reload --port 8001
```
