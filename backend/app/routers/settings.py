from fastapi import APIRouter

from ..audit import log_event
from ..deps import DB, Admin, Reader
from ..schemas import CompanySettings
from ..services.settings_store import get_company, set_company

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/company", response_model=CompanySettings)
def read_company(db: DB, _: Reader):
    return get_company(db)


@router.put("/company", response_model=CompanySettings)
def write_company(body: CompanySettings, db: DB, user: Admin):
    log_event(db, "settings", "company", "updated", user, body.model_dump())
    return set_company(db, body)
