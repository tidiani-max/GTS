from .conftest import PW, login


def test_protected_routes_require_token(client):
    for path in ["/api/v1/inquiries", "/api/v1/projects", "/api/v1/users", "/api/v1/reports/overview",
                 "/api/v1/automation/status", "/api/v1/notifications"]:
        r = client.get(path)
        assert r.status_code == 401, path
        assert r.json()["error"]["code"] == "unauthorized"


def test_login_ok_sets_httponly_refresh_cookie(client):
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "super_admin" and "passwordHash" not in str(body)
    assert "httponly" in r.headers["set-cookie"].lower()


def test_login_wrong_password_generic_and_lockout(client):
    for _ in range(5):
        r = login(client, password="wrong")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "invalid_credentials"
    assert login(client).status_code == 401  # locked even with the right password


def test_unknown_email_same_error(client):
    r = client.post("/api/v1/auth/login", json={"email": "nobody@t.io", "password": "x"})
    assert r.status_code == 401 and r.json()["error"]["message"] == "Email ou mot de passe incorrect."


def test_refresh_rotation_and_reuse_detection(client):
    login(client)
    old = client.cookies.get("gst_refresh")
    assert client.post("/api/v1/auth/refresh").status_code == 200
    new = client.cookies.get("gst_refresh")
    assert new != old
    client.cookies.set("gst_refresh", old, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401  # reuse of a rotated token
    client.cookies.set("gst_refresh", new, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401  # whole family revoked


def test_logout_revokes_refresh(client):
    login(client)
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_invalid_and_tampered_token(client):
    r = client.get("/api/v1/inquiries", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401


def test_rbac_matrix(client, auth, make_inquiry):
    ref = make_inquiry()
    ro, staff, admin, sup = auth("readonly"), auth("staff"), auth("admin"), auth("super_admin")
    assert client.get("/api/v1/inquiries", headers=ro).status_code == 200
    assert client.patch(f"/api/v1/inquiries/{ref}", json={"priority": "Haute"}, headers=ro).status_code == 403
    assert client.post(f"/api/v1/inquiries/{ref}/notes", json={"body": "x"}, headers=ro).status_code == 403
    assert client.patch(f"/api/v1/inquiries/{ref}", json={"priority": "Haute"}, headers=staff).status_code == 200
    assert client.delete(f"/api/v1/inquiries/{ref}", headers=staff).status_code == 403
    assert client.post("/api/v1/services", json={"title": "Nouveau"}, headers=staff).status_code == 403
    assert client.post("/api/v1/services", json={"title": "Nouveau"}, headers=admin).status_code == 201
    assert client.get("/api/v1/automation/status", headers=staff).status_code == 403
    assert client.get("/api/v1/automation/status", headers=admin).status_code == 200
    assert client.get("/api/v1/audit", headers=staff).status_code == 403
    body = {"name": "Neo", "email": "neo@t.io", "password": "Str0ngPassword!"}
    assert client.post("/api/v1/users", json=body, headers=admin).status_code == 403
    assert client.post("/api/v1/users", json=body, headers=sup).status_code == 201
    assert client.delete(f"/api/v1/inquiries/{ref}", headers=admin).status_code == 204


def test_deactivated_user_token_stops_working(client, auth):
    sup, staff = auth("super_admin"), auth("staff")
    uid = [u for u in client.get("/api/v1/users", headers=sup).json() if u["role"] == "staff"][0]["id"]
    assert client.patch(f"/api/v1/users/{uid}", json={"active": False}, headers=sup).status_code == 200
    assert client.get("/api/v1/inquiries", headers=staff).status_code == 401


def test_cannot_remove_last_super_admin(client, auth):
    sup = auth("super_admin")
    uid = [u for u in client.get("/api/v1/users", headers=sup).json() if u["role"] == "super_admin"][0]["id"]
    r = client.patch(f"/api/v1/users/{uid}", json={"role": "admin"}, headers=sup)
    assert r.status_code == 409 and r.json()["error"]["code"] == "last_super_admin"


def test_change_password(client, auth):
    h = auth("staff")
    assert client.post("/api/v1/auth/change-password", json={"currentPassword": "bad", "newPassword": "NewPassw0rd!x"}, headers=h).status_code == 400
    assert client.post("/api/v1/auth/change-password", json={"currentPassword": PW, "newPassword": "alllowercase1"}, headers=h).status_code == 422
    assert client.post("/api/v1/auth/change-password", json={"currentPassword": PW, "newPassword": "NewPassw0rd!x"}, headers=h).status_code == 204
    assert login(client, "staff", "NewPassw0rd!x").status_code == 200


def test_security_headers_and_error_envelope(client):
    r = client.get("/api/v1/health")
    assert r.json()["status"] == "ok"
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    r = client.get("/api/v1/nope")
    assert r.status_code == 404 and "error" in r.json()
