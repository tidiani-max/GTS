from datetime import date

from .models import Client, Inquiry, InquiryNote, Project, Service, User
from .schemas import InquiryOut, NoteOut, ProjectOut, ServiceOut, UserOut

UNASSIGNED = "Non assigné"
OPEN = ("Nouveau", "À étudier", "En cours")


def note_out(n: InquiryNote) -> NoteOut:
    return NoteOut(id=n.id, body=n.body, author=n.author.name if n.author else "Système", created_at=n.created_at)


def inquiry_out(i: Inquiry, with_notes: bool = False) -> InquiryOut:
    return InquiryOut(
        id=i.reference or f"GST-{i.id}", name=i.name, company=i.company, email=i.email, phone=i.phone,
        service=i.service, message=i.message, status=i.status, priority=i.priority,
        assignee=i.assignee.name if i.assignee else UNASSIGNED, assignee_id=i.assignee_id,
        created_at=i.created_at, follow_up=i.follow_up, unread=i.unread, is_demo=i.is_demo,
        overdue=bool(i.follow_up and i.follow_up < date.today() and i.status in OPEN),
        notes=[note_out(n) for n in i.notes] if with_notes else [])


def project_out(p: Project) -> ProjectOut:
    return ProjectOut(id=p.reference or f"PRJ-{p.id}", name=p.name, client=p.client.name if p.client else "",
                      service=p.service, status=p.status, progress=p.progress, deadline=p.deadline,
                      lead=p.lead.name if p.lead else UNASSIGNED, lead_id=p.lead_id, is_demo=p.is_demo)


def service_out(s: Service) -> ServiceOut:
    return ServiceOut(id=s.reference or f"SER-{s.id}", title=s.title, description=s.description, active=s.active)


def user_out(u: User) -> UserOut:
    return UserOut.model_validate(u)
