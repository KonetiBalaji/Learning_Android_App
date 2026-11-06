from test_learning_flow import account, client


def test_email_password_login_is_case_insensitive_private_and_deletable(client):
    email = "Student.Name+study@Example.test"
    password = "a disposable password"
    new = client.post("/auth/register", json={"username": email, "password": password})
    assert new.status_code == 200
    duplicate = client.post("/auth/register", json={"username": email.lower(), "password": password})
    assert duplicate.status_code == 409
    login = client.post("/auth/login", json={"username": email.upper(), "password": password})
    assert login.status_code == 200
    assert login.json()["owner_id"] == new.json()["owner_id"]
    store = client.app.state.store
    stored = store.db.execute("SELECT name FROM users WHERE id=?", (new.json()["owner_id"],)).fetchone()[0]
    assert stored.startswith("email:") and len(stored) == 70
    assert email.lower() not in stored
    legacy = account(client, "Student.Name")
    assert client.get("/account", headers=legacy).json()["owner_id"] != new.json()["owner_id"]
    removed = client.post("/delete-account", headers={"Origin": "http://testserver"},
                          data={"username": email.lower(), "password": password, "confirm": "yes"})
    assert "were deleted" in removed.text
    assert client.get("/account", headers={"Authorization": "Bearer " + login.json()["token"]}).status_code == 401


def test_malformed_email_cannot_register(client):
    for identifier in ("name..part@example.test", "name@-example.test", "name@example", "name@two@example.test"):
        assert client.post("/auth/register", json={"username": identifier, "password": "a disposable password"}).status_code == 422
