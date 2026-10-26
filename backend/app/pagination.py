from fastapi import Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class PageParams:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100, alias="pageSize")):
        self.page, self.page_size = page, page_size


def paginate(db: Session, stmt, params: PageParams, mapper, unique: bool = False) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    q = stmt.limit(params.page_size).offset((params.page - 1) * params.page_size)
    rows = db.scalars(q).unique().all() if unique else db.scalars(q).all()
    return {"items": [mapper(r) for r in rows], "total": total, "page": params.page,
            "page_size": params.page_size, "pages": max(1, -(-total // params.page_size))}


def order_by_param(model, sort: str, allowed: dict, default: str):
    """sort='-created_at' -> ORDER BY created_at DESC, with a whitelist and stable id tie-break."""
    desc = sort.startswith("-")
    key = sort.lstrip("-+")
    col = allowed.get(key) or allowed[default]
    return [col.desc() if desc else col.asc(), model.id.desc() if desc else model.id.asc()]
