from datetime import timedelta

VALID = {"name": "Awa Diarra", "email": "awa@example.com", "message": "Nous souhaitons un devis pour un site.",
         "service": "Génie civil"}


def test_contact_submission_persists_and_shows_in_admin(client, auth):
    r = client.post("/api/v1/public/contact", json=VALID)
    assert r.status_code == 201
    ref = r.json()["reference"]
    items = client.get("/api/v1/inquiries", headers=auth("staff")).json()["items"]
    assert items[0]["id"] == ref and items[0]["status"] == "Nouveau" and items[0]["unread"] is True


def test_contact_validation(client):
    r = client.post("/api/v1/public/contact", json={**VALID, "email": "bad", "message": "court"})
    assert r.status_code == 422
    fields = {d["field"] for d in r.json()["error"]["details"]}
    assert {"email", "message"} <= fields


def test_contact_honeypot_stores_nothing(client, auth):
    assert client.post("/api/v1/public/contact", json={**VALID, "website": "http://spam"}).status_code == 201
    assert client.get("/api/v1/inquiries", headers=auth("staff")).json()["total"] == 0


def test_contact_duplicate_is_idempotent(client, auth):
    a = client.post("/api/v1/public/contact", json=VALID).json()["reference"]
    b = client.post("/api/v1/public/contact", json=VALID).json()["reference"]
    assert a == b and client.get("/api/v1/inquiries", headers=auth("staff")).json()["total"] == 1


def test_contact_rate_limited(client):
    codes = [client.post("/api/v1/public/contact", json={**VALID, "message": f"Message numéro {i} assez long"}).status_code
             for i in range(7)]
    assert codes[:5] == [201] * 5 and codes[5] == 429


def test_contact_creates_notification_for_admins(client, auth):
    client.post("/api/v1/public/contact", json=VALID)
    n = client.get("/api/v1/notifications", headers=auth("admin")).json()
    assert n["unreadCount"] == 1 and n["items"][0]["kind"] == "new_inquiry"
    assert client.post("/api/v1/notifications/read-all", headers=auth("admin")).status_code == 204
    assert client.get("/api/v1/notifications", headers=auth("admin")).json()["unreadCount"] == 0
    assert client.get("/api/v1/notifications", headers=auth("staff")).json()["unreadCount"] == 0  # staff is not an admin


def test_status_transitions(client, auth, make_inquiry):
    ref, h = make_inquiry(), auth("staff")
    url = f"/api/v1/inquiries/{ref}"
    assert client.patch(url, json={"status": "Résolu"}, headers=h).json()["status"] == "Résolu"
    r = client.patch(url, json={"status": "Rejeté"}, headers=h)  # closed -> rejected is forbidden
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_transition"
    assert client.patch(url, json={"status": "En cours"}, headers=h).status_code == 200  # reopen
    assert client.patch(url, json={"status": "Inconnu"}, headers=h).status_code == 422


def test_update_assign_notes_history(client, auth, make_inquiry):
    ref, h = make_inquiry(), auth("staff")
    users = client.get("/api/v1/users", headers=h).json()
    admin_id = [u for u in users if u["role"] == "admin"][0]["id"]
    r = client.patch(f"/api/v1/inquiries/{ref}", json={"assigneeId": admin_id, "priority": "Urgente",
                                                       "followUp": "2030-01-01"}, headers=h)
    d = r.json()
    assert d["assignee"] == "Admin" and d["priority"] == "Urgente" and d["followUp"] == "2030-01-01"
    assert client.post(f"/api/v1/inquiries/{ref}/notes", json={"body": "  Appel client  "}, headers=h).status_code == 201
    assert client.post(f"/api/v1/inquiries/{ref}/notes", json={"body": ""}, headers=h).status_code == 422
    assert client.get(f"/api/v1/inquiries/{ref}", headers=h).json()["notes"][0]["body"] == "Appel client"
    hist = client.get(f"/api/v1/inquiries/{ref}/history", headers=h).json()
    assert {e["action"] for e in hist} >= {"updated", "note_added"}
    assert client.patch(f"/api/v1/inquiries/{ref}", json={"assigneeId": 9999}, headers=h).status_code == 422
    assert client.get("/api/v1/notifications", headers=auth("admin")).json()["items"][0]["kind"] == "assignment"


def test_filters_search_sort_pagination(client, auth, make_inquiry):
    make_inquiry(name="Alpha", status="Nouveau", priority="Haute", service="Génie civil")
    make_inquiry(name="Bravo", status="En cours", priority="Basse", service="Cloud", email="b@example.com")
    make_inquiry(name="Charlie 100%", status="En cours", priority="Haute", service="Cloud", email="c@example.com")
    h = auth("readonly")
    get = lambda q: client.get(f"/api/v1/inquiries?{q}", headers=h).json()
    assert get("status=En cours")["total"] == 2
    assert get("status=En cours&priority=Haute")["total"] == 1
    assert get("q=alp")["items"][0]["name"] == "Alpha"
    assert get("q=%25")["total"] == 1  # LIKE wildcard is escaped: only the literal "100%"
    assert [i["name"] for i in get("sort=name")["items"]] == ["Alpha", "Bravo", "Charlie 100%"]
    assert [i["name"] for i in get("sort=-name")["items"]][0] == "Charlie 100%"
    p = get("pageSize=2&page=2")
    assert p["total"] == 3 and p["pages"] == 2 and len(p["items"]) == 1
    assert client.get("/api/v1/inquiries?pageSize=1000", headers=h).status_code == 422
    assert get("sort=password_hash")["total"] == 3  # unknown sort keys fall back safely


def test_overdue_filter_and_flag(client, auth, make_inquiry, today):
    make_inquiry(name="Late", follow_up=today - timedelta(days=2), status="En cours")
    make_inquiry(name="Closed", follow_up=today - timedelta(days=2), status="Résolu")
    items = client.get("/api/v1/inquiries?overdue=true", headers=auth("staff")).json()["items"]
    assert [i["name"] for i in items] == ["Late"] and items[0]["overdue"] is True


def test_csv_export_neutralises_formulas(client, auth, make_inquiry):
    make_inquiry(name="=HYPERLINK(\"http://evil\")")
    r = client.get("/api/v1/inquiries/export.csv", headers=auth("readonly"))
    assert r.status_code == 200 and "text/csv" in r.headers["content-type"]
    assert "'=HYPERLINK" in r.text and ",=HYPERLINK" not in r.text


def test_delete_inquiry_audited(client, auth, make_inquiry):
    ref = make_inquiry()
    assert client.delete(f"/api/v1/inquiries/{ref}", headers=auth("admin")).status_code == 204
    assert client.get(f"/api/v1/inquiries/{ref}", headers=auth("admin")).status_code == 404
    assert any(e["action"].endswith("deleted") for e in client.get("/api/v1/audit", headers=auth("admin")).json()["items"])
