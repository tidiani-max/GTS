import os

# Test configuration must be set BEFORE the app is imported. Tests DROP ALL TABLES, so they never use DATABASE_URL:
# they use TEST_DATABASE_URL (e.g. a dedicated PostgreSQL database) or a throw-away SQLite file.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test.db")
os.environ["ENVIRONMENT"] = "test"
os.environ["EMAIL_MODE"] = "disabled"  # never send mail in tests
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-0123456789"

import smtplib  # noqa: E402
from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ratelimit  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Inquiry, User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.settings_store import get_company, set_company  # noqa: E402

PW = "TestPassw0rd!"


@pytest.fixture(autouse=True)
def _no_smtp(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("SMTP must never be used in tests")
    monkeypatch.setattr(smtplib, "SMTP", boom)


@pytest.fixture(autouse=True)
def db_reset():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    ratelimit.reset()
    with SessionLocal() as db:
        for name, role in [("Super", "super_admin"), ("Admin", "admin"), ("Staff", "staff"), ("Reader", "readonly")]:
            db.add(User(name=name, email=f"{role}@t.io", role=role, password_hash=hash_password(PW)))
        set_company(db, get_company(db))
        db.commit()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def login(client, role="super_admin", password=PW):
    r = client.post("/api/v1/auth/login", json={"email": f"{role}@t.io", "password": password})
    return r


@pytest.fixture()
def auth(client):
    """auth('admin') -> headers"""
    def _auth(role="admin"):
        r = login(client, role)
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['accessToken']}"}
    return _auth


@pytest.fixture()
def make_inquiry():
    def _make(**kw):
        with SessionLocal() as db:
            data = dict(name="Jean Test", email="jean@example.com", message="Message de test suffisamment long.",
                        service="Génie civil", status="Nouveau", priority="Normale")
            data.update(kw)
            i = Inquiry(**data)
            db.add(i)
            db.flush()
            i.reference = f"GST-{1000 + i.id}"
            db.commit()
            return i.reference
    return _make


@pytest.fixture()
def today():
    return date.today()
