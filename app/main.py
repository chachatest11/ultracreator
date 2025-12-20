from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from .db import init_db, get_db
from .api import (
    categories_router,
    channels_router,
    search_router,
    downloads_router,
    settings_router,
    api_keys_router
)

# FastAPI 앱 생성
app = FastAPI(title="YouTube Shorts Downloader")

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# API 라우터 등록
app.include_router(categories_router)
app.include_router(channels_router)
app.include_router(search_router)
app.include_router(downloads_router)
app.include_router(settings_router)
app.include_router(api_keys_router)


@app.on_event("startup")
def startup_event():
    """앱 시작 시 DB 초기화"""
    init_db()
    print("Database initialized")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """메인 페이지"""
    # 카테고리 목록 조회
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, created_at
            FROM categories
            ORDER BY id ASC
        """)
        category_rows = cursor.fetchall()
        categories = [
            {
                "id": row[0],
                "name": row[1],
                "created_at": row[2]
            }
            for row in category_rows
        ]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": categories
        }
    )


@app.get("/health")
def health_check():
    """헬스 체크"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
