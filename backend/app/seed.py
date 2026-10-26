"""Seed command: `python -m app.seed` (idempotent). Everything created here is flagged is_demo=True.
Demo clients/inquiries/projects are FICTIONAL examples (example.com addresses), not real GST customers."""

import argparse
import logging
from datetime import date, timedelta

from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .models import Client, Inquiry, InquiryNote, Project, Service, User, utcnow
from .security import hash_password
from .services.settings_store import (
    get_automation,
    get_company,
    set_automation,
    set_company,
)

log = logging.getLogger("gst.seed")
SERVICES = [
    (
        "Télémétrie & Télésurveillance",
        "Supervision en temps réel et reporting centralisé.",
    ),
    ("Génie civil", "Terrassement, fondations et infrastructures."),
    ("Services environnementaux", "Prévention, traitement et suivi de sites."),
    ("Cloud & DevOps", "Migration, hébergement et automatisation."),
]
DEMO_USERS = [
    ("Fatou K.", "fatou@example.com", "admin", "Responsable opérations"),
    ("Ibrahim S.", "ibrahim@example.com", "staff", "Ingénieur projet"),
    ("Amadou D.", "amadou@example.com", "staff", "Expert systèmes"),
    ("Lecteur démo", "lecteur@example.com", "readonly", "Consultation"),
]
# (name, company, service, message, status, priority, assignee idx|None, created days ago, follow-up offset days|None)
INQUIRIES = [
    (
        "Mamadou Diallo",
        "Sahel Distribution (démo)",
        "Télésurveillance",
        "Besoin d’une étude pour superviser trois sites à Bamako.",
        "Nouveau",
        "Haute",
        None,
        3,
        3,
    ),
    (
        "Aïssata Traoré",
        "Exemple Énergie (démo)",
        "Télémétrie énergétique",
        "Demande de démonstration pour un tableau de bord énergétique.",
        "À étudier",
        "Urgente",
        0,
        4,
        0,
    ),
    (
        "Oumar Konaté",
        "Bâtir Mali (démo)",
        "Génie civil",
        "Étude de fondations et supports techniques.",
        "En cours",
        "Normale",
        1,
        7,
        2,
    ),
    (
        "Fanta Coulibaly",
        "Client exemple",
        "Services environnementaux",
        "Programme de prévention et traitement de site.",
        "Résolu",
        "Normale",
        0,
        13,
        None,
    ),
    (
        "Seydou Maïga",
        "Projet Démo",
        "Cloud & DevOps",
        "Migration applicative et hébergement.",
        "Rejeté",
        "Basse",
        2,
        17,
        None,
    ),
    (
        "Mariama Sangaré",
        "Commerce Plus (démo)",
        "Sécurité systèmes",
        "Audit de sécurité du réseau interne.",
        "En cours",
        "Haute",
        2,
        20,
        -3,
    ),
    (
        "Bakary Keïta",
        "Transport Démo",
        "Optimisation télécoms",
        "Optimisation réseau sur quatre sites.",
        "Résolu",
        "Normale",
        1,
        27,
        None,
    ),
    (
        "Kadiatou Touré",
        "ONG Exemple",
        "Solutions énergétiques",
        "Étude photovoltaïque pour un bureau régional.",
        "À étudier",
        "Haute",
        0,
        34,
        -1,
    ),
]
PROJECTS = [
    (
        "Supervision multi-sites",
        "Client télécom  exemple",
        "Télémétrie",
        "En cours",
        72,
        60,
        1,
    ),
    (
        "Audit infrastructure réseau",
        "Client privé  exemple",
        "Télécoms",
        "En cours",
        46,
        35,
        2,
    ),
    (
        "Traitement environnemental",
        "Institution  exemple",
        "Environnement",
        "Planifié",
        15,
        90,
        0,
    ),
    ("Installation photovoltaïque", "ONG  exemple", "Énergie", "Terminé", 100, -20, 1),
]


def seed(demo: bool = True) -> None:
    s = get_settings()
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == s.seed_admin_email))
        if not admin:
            db.add(
                User(
                    name="Administrateur GST",
                    email=s.seed_admin_email,
                    role="super_admin",
                    job_title="Direction des opérations",
                    password_hash=hash_password(s.seed_admin_password),
                    is_demo=True,
                    password_changed_at=utcnow(),
                )
            )
        if not db.get(
            __import__("app.models", fromlist=["Setting"]).Setting, "company"
        ):
            set_company(db, get_company(db))
        set_automation(db, get_automation(db)) if not db.get(
            __import__("app.models", fromlist=["Setting"]).Setting, "automation"
        ) else None
        if not db.scalar(select(Service.id).limit(1)):
            for i, (t, d) in enumerate(SERVICES, 1):
                db.add(Service(title=t, description=d, sort_order=i))
            db.flush()
            for sv in db.scalars(select(Service)).all():
                sv.reference = f"SER-{sv.id:02d}"
        if demo and not db.scalar(
            select(User.id).where(User.email == DEMO_USERS[0][1])
        ):
            users = []
            for n, e, r, t in DEMO_USERS:
                u = User(
                    name=n,
                    email=e,
                    role=r,
                    job_title=t,
                    password_hash=hash_password(s.seed_admin_password),
                    is_demo=True,
                )
                db.add(u)
                users.append(u)
            db.flush()
            today, now = date.today(), utcnow()
            for idx, (n, co, sv, msg, st, pr, a, ago, fu) in enumerate(INQUIRIES):
                i = Inquiry(
                    name=n,
                    company=co,
                    email=f"{n.split()[0].lower().replace('ï', 'i').replace('ï', 'i')}.{idx}@example.com",
                    phone="+223 70 00 00 0" + str(idx),
                    service=sv,
                    message=msg,
                    status=st,
                    priority=pr,
                    assignee=users[a] if a is not None else None,
                    created_at=now - timedelta(days=ago),
                    follow_up=today + timedelta(days=fu) if fu is not None else None,
                    unread=st == "Nouveau",
                    is_demo=True,
                    source="demo",
                    resolved_at=(now - timedelta(days=max(ago - 3, 0)))
                    if st in ("Résolu", "Rejeté")
                    else None,
                )
                db.add(i)
                db.flush()
                i.reference = f"GST-{1000 + i.id}"
                if st in ("En cours", "Résolu"):
                    db.add(
                        InquiryNote(
                            inquiry_id=i.id,
                            author_id=users[0].id,
                            body="Note de démonstration : contact établi.",
                        )
                    )
            for k, (n, c, sv, st, pg, dl, lead) in enumerate(PROJECTS):
                cl = db.scalar(select(Client).where(Client.name == c)) or Client(
                    name=c, is_demo=True
                )
                db.add(cl)
                db.flush()
                p = Project(
                    name=n,
                    client=cl,
                    service=sv,
                    status=st,
                    progress=pg,
                    deadline=today + timedelta(days=dl),
                    lead=users[lead],
                    is_demo=True,
                )
                db.add(p)
                db.flush()
                p.reference = f"PRJ-{p.id:03d}"
        db.commit()
    log.info("Seed complete (demo=%s)", demo)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--no-demo",
        action="store_true",
        help="only create the admin account, settings and services",
    )
    seed(demo=not ap.parse_args().no_demo)
