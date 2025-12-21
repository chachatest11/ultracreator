from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List
from ..db import get_db
from ..models import Category

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str


class CategoryUpdate(BaseModel):
    name: str


@router.get("/")
def get_categories():
    """모든 카테고리 조회 (채널 개수 포함)"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 전체 채널 개수
        cursor.execute("SELECT COUNT(*) FROM channels")
        total_count = cursor.fetchone()[0]

        # 각 카테고리별 채널 개수 포함 (display_order로 정렬)
        cursor.execute("""
            SELECT c.id, c.name, c.created_at, c.display_order, COUNT(ch.id) as channel_count
            FROM categories c
            LEFT JOIN channels ch ON c.id = ch.category_id
            GROUP BY c.id, c.name, c.created_at, c.display_order
            ORDER BY c.display_order ASC, c.id ASC
        """)
        rows = cursor.fetchall()

        categories = []
        for row in rows:
            category_dict = {
                "id": row[0],
                "name": row[1],
                "created_at": row[2],
                "display_order": row[3],
                "channel_count": row[4]
            }
            categories.append(category_dict)

        return {
            "categories": categories,
            "total_count": total_count
        }


@router.post("/")
def create_category(data: CategoryCreate):
    """새 카테고리 생성"""
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="카테고리 이름은 필수입니다")

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO categories (name, created_at)
                VALUES (?, ?)
            """, (data.name.strip(), datetime.now().isoformat()))
            conn.commit()
            category_id = cursor.lastrowid

            # 생성된 카테고리 조회
            cursor.execute("""
                SELECT id, name, created_at
                FROM categories
                WHERE id = ?
            """, (category_id,))
            row = cursor.fetchone()
            category = Category.from_row(row)
            return {"category": category.to_dict()}

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(status_code=400, detail="이미 존재하는 카테고리 이름입니다")
            raise HTTPException(status_code=500, detail=str(e))


@router.put("/{category_id}")
def update_category(category_id: int, data: CategoryUpdate):
    """카테고리 이름 수정"""
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="카테고리 이름은 필수입니다")

    with get_db() as conn:
        cursor = conn.cursor()

        # 카테고리 존재 확인
        cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")

        try:
            cursor.execute("""
                UPDATE categories
                SET name = ?
                WHERE id = ?
            """, (data.name.strip(), category_id))
            conn.commit()

            # 수정된 카테고리 조회
            cursor.execute("""
                SELECT id, name, created_at
                FROM categories
                WHERE id = ?
            """, (category_id,))
            row = cursor.fetchone()
            category = Category.from_row(row)
            return {"category": category.to_dict()}

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(status_code=400, detail="이미 존재하는 카테고리 이름입니다")
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{category_id}")
def delete_category(category_id: int):
    """카테고리 삭제 (채널은 기본 카테고리로 이동)"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 카테고리 존재 확인
        cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")

        # 기본 카테고리(id=1) 삭제 방지
        if category_id == 1:
            raise HTTPException(status_code=400, detail="기본 카테고리는 삭제할 수 없습니다")

        # 해당 카테고리의 모든 채널을 기본 카테고리로 이동
        cursor.execute("""
            UPDATE channels
            SET category_id = 1
            WHERE category_id = ?
        """, (category_id,))

        # 카테고리 삭제
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()

        return {"success": True, "message": "카테고리가 삭제되었습니다"}


@router.put("/{category_id}/reorder")
def reorder_category(category_id: int, direction: str):
    """카테고리 순서 변경 (direction: 'up' 또는 'down')"""
    if direction not in ['up', 'down']:
        raise HTTPException(status_code=400, detail="direction은 'up' 또는 'down'이어야 합니다")

    with get_db() as conn:
        cursor = conn.cursor()

        # 현재 카테고리 조회
        cursor.execute("""
            SELECT id, display_order
            FROM categories
            WHERE id = ?
        """, (category_id,))
        current = cursor.fetchone()

        if not current:
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")

        current_id, current_order = current[0], current[1]

        # 교환할 카테고리 찾기
        if direction == 'up':
            # 현재보다 order가 작은 것 중 가장 큰 것
            cursor.execute("""
                SELECT id, display_order
                FROM categories
                WHERE display_order < ?
                ORDER BY display_order DESC
                LIMIT 1
            """, (current_order,))
        else:  # down
            # 현재보다 order가 큰 것 중 가장 작은 것
            cursor.execute("""
                SELECT id, display_order
                FROM categories
                WHERE display_order > ?
                ORDER BY display_order ASC
                LIMIT 1
            """, (current_order,))

        target = cursor.fetchone()

        if not target:
            # 이미 맨 위/아래에 있음
            return {"success": True, "message": "이미 최" + ('상단' if direction == 'up' else '하단') + "입니다"}

        target_id, target_order = target[0], target[1]

        # 순서 교환
        cursor.execute("""
            UPDATE categories
            SET display_order = ?
            WHERE id = ?
        """, (target_order, current_id))

        cursor.execute("""
            UPDATE categories
            SET display_order = ?
            WHERE id = ?
        """, (current_order, target_id))

        conn.commit()

        return {"success": True, "message": "순서가 변경되었습니다"}
