# Xiaohongshu Video Downloader - 설치 및 실행 가이드

## 🍎 맥에서 처음 시작하기 (Git 클론부터)

### 1. 저장소 클론
```bash
# 터미널 열기 (Cmd + Space → "Terminal" 입력)

# 원하는 위치로 이동 (예: 홈 디렉토리)
cd ~

# 저장소 클론
git clone https://github.com/chachatest11/ultracreator.git

# 프로젝트 폴더로 이동
cd ultracreator

# 작업 브랜치로 체크아웃
git checkout claude/xiaohongshu-video-downloader-qMlsK
```

### 2. VSCode로 프로젝트 열기

**터미널에서:**
```bash
code .
```

**또는 VSCode GUI에서:**
- File → Open Folder → `ultracreator` 폴더 선택

### 3. 의존성 설치
VSCode 터미널에서 (Control + ` 또는 Ctrl + `):

```bash
pip3 install -r requirements.txt
```

### 4. 서버 실행

**가장 간단한 방법:**
```bash
python3 app/main.py
```

**또는:**
```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 브라우저 접속
```
http://localhost:8000
```

---

## 🚀 한 번에 실행 (복사/붙여넣기)

```bash
cd ~
git clone https://github.com/chachatest11/ultracreator.git
cd ultracreator
git checkout claude/xiaohongshu-video-downloader-qMlsK
pip3 install -r requirements.txt
python3 app/main.py
```

---

## ⚙️ VSCode에서 편하게 실행하기 (선택사항)

### .vscode 폴더 설정

프로젝트 루트에 `.vscode` 폴더를 만들고 설정 파일을 추가하세요:

#### .vscode/launch.json (F5로 디버깅)
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run Xiaohongshu Downloader",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000"
            ],
            "jinja": true,
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

#### .vscode/tasks.json (Cmd+Shift+B로 실행)
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Run Server",
            "type": "shell",
            "command": "python3",
            "args": [
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000"
            ],
            "group": {
                "kind": "build",
                "isDefault": true
            },
            "presentation": {
                "reveal": "always",
                "panel": "new"
            },
            "problemMatcher": []
        }
    ]
}
```

### VSCode 단축키 (맥)

설정 후 사용 가능한 단축키:
- **Cmd + Shift + B**: 서버 빠르게 실행
- **F5** (또는 Fn + F5): 디버깅 모드로 실행
- **Cmd + Shift + P** → "Tasks: Run Task" → "Run Server"

---

## 🔧 문제 해결

### "command not found: python"
맥에서는 `python3` 사용:
```bash
python3 --version
```

### "command not found: pip"
```bash
pip3 --version
```

### "command not found: git"
```bash
# Homebrew로 Git 설치
brew install git
```

### Homebrew 없음
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### VSCode에서 "code" 명령어 안됨
VSCode에서:
1. **Cmd + Shift + P**
2. "Shell Command: Install 'code' command in PATH" 입력 및 실행

### 포트가 이미 사용 중
```bash
# 다른 포트 사용
python3 -m uvicorn app.main:app --reload --port 8001
```

### yt-dlp 없음 (다운로드 기능 사용 시 필수)
```bash
# Homebrew로 설치 (추천)
brew install yt-dlp

# 또는 pip으로 설치
pip3 install yt-dlp
```

---

## 📦 가상환경 사용 (선택사항, 권장)

더 깔끔한 환경 관리를 원한다면:

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 서버 실행
python -m uvicorn app.main:app --reload

# 사용 완료 후 비활성화
deactivate
```

---

## 🎯 빠른 시작 체크리스트

- [ ] Git 설치 확인: `git --version`
- [ ] Python 설치 확인: `python3 --version`
- [ ] 저장소 클론: `git clone ...`
- [ ] 브랜치 체크아웃: `git checkout claude/xiaohongshu-video-downloader-qMlsK`
- [ ] 의존성 설치: `pip3 install -r requirements.txt`
- [ ] yt-dlp 설치: `brew install yt-dlp`
- [ ] 서버 실행: `python3 app/main.py`
- [ ] 브라우저 접속: `http://localhost:8000`

---

## 📝 두 번째 실행부터는

```bash
cd ultracreator
python3 app/main.py
```

그게 다입니다! 🎉
