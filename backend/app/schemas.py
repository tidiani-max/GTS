"""Pydantic schemas. JSON keys are camelCase to match the existing frontend types."""
from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel

T = TypeVar("T")
InquiryStatus = Literal["Nouveau", "À étudier", "En cours", "Résolu", "Rejeté"]
Priority = Literal["Basse", "Normale", "Haute", "Urgente"]
ProjectStatus = Literal["Planifié", "En cours", "Suspendu", "Terminé"]
Role = Literal["readonly", "staff", "admin", "super_admin"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True,
                              str_strip_whitespace=True)


class Page(CamelModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


# ---------- auth / users ----------
class LoginIn(CamelModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserOut(CamelModel):
    id: int
    name: str
    email: str
    role: Role
    job_title: str
    active: bool
    is_demo: bool = False
    last_login_at: datetime | None = None
    prefs: dict = {}


class LoginOut(CamelModel):
    access_token: str
    expires_in: int
    user: UserOut


class UserCreate(CamelModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: Role = "staff"
    job_title: str = Field("Collaborateur", max_length=120)
    password: str = Field(min_length=10, max_length=128)


class UserUpdate(CamelModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    role: Role | None = None
    job_title: str | None = Field(None, max_length=120)
    active: bool | None = None
    password: str | None = Field(None, min_length=10, max_length=128)


class ProfileUpdate(CamelModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    email: EmailStr | None = None
    job_title: str | None = Field(None, max_length=120)
    prefs: dict[str, bool] | None = None


class PasswordChange(CamelModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


# ---------- inquiries ----------
class ContactIn(CamelModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    message: str = Field(min_length=10, max_length=5000)
    service: str = Field("Demande générale", max_length=200)
    phone: str = Field("", max_length=60)
    company: str = Field("", max_length=200)
    website: str = Field("", max_length=200)  # honeypot: real users leave it empty


class NoteOut(CamelModel):
    id: int
    body: str
    author: str
    created_at: datetime


class HistoryOut(CamelModel):
    id: int
    action: str
    actor: str
    details: dict
    created_at: datetime


class InquiryOut(CamelModel):
    id: str  # public reference, e.g. GST-1048
    name: str
    company: str
    email: str
    phone: str
    service: str
    message: str
    status: InquiryStatus
    priority: Priority
    assignee: str
    assignee_id: int | None
    created_at: datetime
    follow_up: date | None
    unread: bool
    overdue: bool
    is_demo: bool
    notes: list[NoteOut] = []


class InquiryUpdate(CamelModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    company: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=60)
    service: str | None = Field(None, max_length=200)
    status: InquiryStatus | None = None
    priority: Priority | None = None
    assignee_id: int | None = None
    follow_up: date | None = None
    unread: bool | None = None


class InquiryCreate(ContactIn):
    """Manual creation by staff (phone call, email...)."""
    status: InquiryStatus = "Nouveau"
    priority: Priority = "Normale"
    assignee_id: int | None = None
    follow_up: date | None = None


class NoteIn(CamelModel):
    body: str = Field(min_length=1, max_length=2000)


# ---------- projects / services ----------
class ProjectIn(CamelModel):
    name: str = Field(min_length=2, max_length=200)
    client: str = Field("", max_length=200)
    service: str = Field("", max_length=200)
    status: ProjectStatus = "Planifié"
    progress: int = Field(0, ge=0, le=100)
    deadline: date | None = None
    lead_id: int | None = None


class ProjectPatch(CamelModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    client: str | None = Field(None, max_length=200)
    service: str | None = Field(None, max_length=200)
    status: ProjectStatus | None = None
    progress: int | None = Field(None, ge=0, le=100)
    deadline: date | None = None
    lead_id: int | None = None


class ProjectOut(CamelModel):
    id: str
    name: str
    client: str
    service: str
    status: ProjectStatus
    progress: int
    deadline: date | None
    lead: str
    lead_id: int | None
    is_demo: bool


class ServiceIn(CamelModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field("", max_length=2000)
    active: bool = True


class ServicePatch(CamelModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
    active: bool | None = None


class ServiceOut(CamelModel):
    id: str
    title: str
    description: str
    active: bool


class ClientOut(CamelModel):
    id: int
    name: str
    is_demo: bool


# ---------- notifications / settings / automation ----------
class NotificationOut(CamelModel):
    id: int
    kind: str
    title: str
    body: str
    link: str
    read: bool
    created_at: datetime


class CompanySettings(CamelModel):
    name: str = Field(max_length=200)
    email: str = Field("", max_length=254)
    address: str = Field("", max_length=500)
    phone: str = Field("", max_length=100)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        if v and ("@" not in v or " " in v):
            raise ValueError("Adresse email invalide")
        return v


class AutomationConfig(CamelModel):
    reminders_enabled: bool = True
    reminders_every_minutes: int = Field(60, ge=5, le=1440)
    reminder_lead_days: int = Field(0, ge=0, le=14)
    reminder_min_gap_hours: int = Field(24, ge=1, le=168)
    max_reminders: int = Field(5, ge=1, le=20)
    overdue_enabled: bool = True
    overdue_every_minutes: int = Field(360, ge=15, le=1440)
    new_inquiry_enabled: bool = True
    notify_assignee: bool = True
    summary_enabled: bool = True
    summary_weekday: int = Field(0, ge=0, le=6)  # 0 = Monday
    summary_hour: int = Field(7, ge=0, le=23)  # UTC (Bamako = UTC+0)
    cleanup_enabled: bool = True
    retention_days: int = Field(90, ge=7, le=3650)
    extra_recipients: list[EmailStr] = Field(default_factory=list, max_length=10)
    dry_run: bool = False  # global: scheduled jobs only report what they would do


class JobRunOut(CamelModel):
    id: int
    job: str
    trigger: str
    dry_run: bool
    status: str
    started_at: datetime
    finished_at: datetime | None
    summary: dict
    error: str


class EmailOut(CamelModel):
    id: int
    to_email: str
    subject: str
    status: str
    attempts: int
    last_error: str
    created_at: datetime
    sent_at: datetime | None
