VEHICLE = {
    "plate": "34 abc 123",
    "owner": "Ada Lovelace",
    "description": "Resident",
    "active": True,
    "valid_from": "2026-01-01",
    "valid_until": "2027-01-01",
    "allowed_days": [0, 1, 2, 3, 4],
    "allowed_start_time": "07:30:00",
    "allowed_end_time": "22:00:00",
    "notes": None,
}


def test_vehicle_crud_normalizes_plate_and_persists_rules(client) -> None:
    created = client.post("/api/v1/vehicles", json=VEHICLE)

    assert created.status_code == 201
    assert created.json()["plate"] == "34ABC123"
    vehicle_id = created.json()["id"]

    listed = client.get("/api/v1/vehicles")
    assert listed.status_code == 200
    assert listed.json()[0]["allowed_days"] == [0, 1, 2, 3, 4]

    updated = client.put(
        f"/api/v1/vehicles/{vehicle_id}",
        json={**VEHICLE, "owner": "Grace Hopper", "active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["owner"] == "Grace Hopper"
    assert updated.json()["active"] is False

    assert client.delete(f"/api/v1/vehicles/{vehicle_id}").status_code == 204
    assert client.get("/api/v1/vehicles").json() == []


def test_vehicle_api_rejects_invalid_and_duplicate_plates(client) -> None:
    assert client.post("/api/v1/vehicles", json=VEHICLE).status_code == 201
    assert client.post("/api/v1/vehicles", json=VEHICLE).status_code == 409
    invalid = client.post("/api/v1/vehicles", json={**VEHICLE, "plate": "INVALID"})
    assert invalid.status_code == 422
