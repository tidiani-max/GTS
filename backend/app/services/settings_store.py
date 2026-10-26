from sqlalchemy.orm import Session

from ..models import Setting
from ..schemas import AutomationConfig, CompanySettings

DEFAULT_COMPANY = {"name": "Global Services Technologie", "email": "dcheick93@hotmail.com",
                   "address": "Hamdallaye ACI-2000 · Rue 420 Porte 437 · BP 2485 Bamako, Mali",
                   "phone": "+223 20 22 33 44 / +223 76 54 32 10"}


def get_company(db: Session) -> CompanySettings:
    row = db.get(Setting, "company")
    return CompanySettings(**{**DEFAULT_COMPANY, **(row.value if row else {})})


def set_company(db: Session, value: CompanySettings) -> CompanySettings:
    row = db.get(Setting, "company") or Setting(key="company")
    row.value = value.model_dump(mode="json", by_alias=False)
    db.add(row)
    return value


def get_automation(db: Session) -> AutomationConfig:
    row = db.get(Setting, "automation")
    return AutomationConfig(**(row.value if row else {}))


def set_automation(db: Session, value: AutomationConfig) -> AutomationConfig:
    row = db.get(Setting, "automation") or Setting(key="automation")
    row.value = value.model_dump(mode="json", by_alias=False)
    db.add(row)
    return value
