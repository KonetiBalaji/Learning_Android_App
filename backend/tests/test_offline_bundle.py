from test_learning_flow import account, client, upload


def test_offline_bundle_is_owned_confirmed_bounded_and_has_no_private_scan_fields(client):
    owner = account(client, "offline-owner")
    other = account(client, "offline-other")
    doc = upload(client, owner)
    path = f'/documents/{doc["id"]}/offline-bundle'
    assert client.get(path, headers=other).status_code == 404
    bundle = client.get(path, headers=owner).json()
    assert bundle["owner_id"] == client.get("/account", headers=owner).json()["owner_id"]
    assert bundle["schema_version"] == 1
    assert bundle["expires_at"] == doc["created"] + 30 * 86400
    assert bundle["cached_at"] < bundle["expires_at"]
    assert bundle["passages"][0]["text"].startswith("Mitochondria")
    assert not any(k.startswith("_") for k in bundle["document"])
    assert "storage.key" not in str(bundle)
    store = client.app.state.store
    value = store.get(doc["id"], bundle["owner_id"], "document")
    value["processing_state"] = "needs_review"
    store.save(doc["id"], bundle["owner_id"], "document", doc["id"], value["created"], value)
    assert client.get(path, headers=owner).status_code == 409
    assert client.delete(f'/documents/{doc["id"]}', headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
