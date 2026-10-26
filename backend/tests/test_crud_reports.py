def test_services_crud_and_public_listing(client, auth):
    h = auth("admin")
    s = client.post("/api/v1/services", json={"title": "Nouvelle offre", "description": "d", "active": False}, headers=h).json()
    assert s["id"].startswith("SER-")
    assert client.get("/api/v1/public/services").json() == []  # inactive services are hidden from the public site
    assert client.patch(f"/api/v1/services/{s['id']}", json={"active": True}, headers=h).json()["active"] is True
    assert [x["title"] for x in client.get("/api/v1/public/services").json()] == ["Nouvelle offre"]
    assert client.delete(f"/api/v1/services/{s['id']}", headers=h).status_code == 204
    assert client.delete(f"/api/v1/services/{s['id']}", headers=h).status_code == 404


def test_projects_crud_client_autocreate_and_validation(client, auth):
    h = auth("admin")
    lead = client.get("/api/v1/users", headers=h).json()[0]["id"]
    p = client.post("/api/v1/projects", json={"name": "Projet A", "client": "ACME", "service": "Énergie",
                                              "progress": 40, "leadId": lead}, headers=h)
    assert p.status_code == 201
    p = p.json()
    assert p["client"] == "ACME" and p["lead"] and p["id"].startswith("PRJ-")
    assert client.post("/api/v1/projects", json={"name": "Projet B", "client": "acme"}, headers=h).status_code == 201
    assert [c["name"] for c in client.get("/api/v1/clients", headers=h).json()] == ["ACME"]  # case-insensitive reuse
    assert client.post("/api/v1/projects", json={"name": "X", "progress": 150}, headers=h).status_code == 422
    r = client.patch(f"/api/v1/projects/{p['id']}", json={"status": "Terminé", "progress": 100}, headers=h)
    assert r.json()["status"] == "Terminé"
    assert client.get("/api/v1/projects?status=Terminé", headers=h).json()["total"] == 1
    assert client.get("/api/v1/projects?q=acme", headers=h).json()["total"] == 2
    assert client.get("/api/v1/projects/export.csv", headers=h).status_code == 200
    assert client.delete(f"/api/v1/projects/{p['id']}", headers=h).status_code == 204


def test_settings_and_profile(client, auth):
    h = auth("admin")
    c = client.put("/api/v1/settings/company", json={"name": "GST", "email": "a@b.ml", "address": "Bamako"}, headers=h)
    assert c.status_code == 200 and client.get("/api/v1/public/company").json()["name"] == "GST"
    assert client.put("/api/v1/settings/company", json={"name": "GST", "email": "bad email"}, headers=auth("staff")).status_code == 403
    r = client.patch("/api/v1/me", json={"name": "Nouveau Nom", "prefs": {"new_inquiry": False, "evil": True}}, headers=h)
    assert r.json()["name"] == "Nouveau Nom" and r.json()["prefs"]["new_inquiry"] is False and "evil" not in r.json()["prefs"]


def test_reports_computed_from_data(client, auth, make_inquiry):
    make_inquiry(status="Nouveau")
    r = make_inquiry(status="En cours")
    make_inquiry(status="En cours", service="Cloud")
    client.patch(f"/api/v1/inquiries/{r}", json={"status": "Résolu"}, headers=auth("staff"))
    d = client.get("/api/v1/reports/overview?range=6m", headers=auth("readonly")).json()
    assert d["kpis"]["totalInquiries"] == 3 and d["kpis"]["toTreat"] == 1
    assert d["kpis"]["resolutionRate"] == 33 and d["kpis"]["avgResolutionDays"] is not None
    assert len(d["trend"]) == 6 and sum(t["demandes"] for t in d["trend"]) == 3
    assert {x["name"]: x["value"] for x in d["byService"]} == {"Génie civil": 2, "Cloud": 1}
    assert client.get("/api/v1/reports/overview?range=bad", headers=auth("readonly")).status_code == 422
    assert client.get("/api/v1/reports/overview.csv", headers=auth("readonly")).status_code == 200
