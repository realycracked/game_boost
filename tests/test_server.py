"""API locale : routes principales et protections (Host, jeton)."""

import pytest
from fastapi.testclient import TestClient

from overdrive import server

# Sans bloc ``with`` : le cycle de vie (préchargement des visuels depuis
# Internet) n'est pas déclenché, les tests restent hors ligne.
client = TestClient(server.app, base_url="http://127.0.0.1")


@pytest.mark.parametrize("path", [
    "/api/status", "/api/settings", "/api/tweaks", "/api/games",
    "/api/quiz", "/api/programs", "/api/crosshairs", "/api/art",
])
def test_main_routes_answer(path):
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert response.json() is not None


def test_status_reports_app_and_version():
    status = client.get("/api/status").json()
    assert status["app"] == "Overdrive"
    assert status["version"]


def test_interface_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "Overdrive" in response.text


def test_foreign_host_is_rejected():
    """Protection contre le DNS rebinding : seul un Host local est accepté."""
    response = client.get("/api/status", headers={"Host": "evil.example"})
    assert response.status_code == 400


def test_network_mode_requires_token():
    server.configure_security(token="jeton-de-test")
    try:
        assert client.get("/api/status").status_code == 401
        ok = client.get("/api/status", headers={"X-Overdrive-Token": "jeton-de-test"})
        assert ok.status_code == 200
    finally:
        server.configure_security(token=None)
        client.cookies.clear()


def test_unknown_art_is_404():
    assert client.get("/api/art/inconnu/cover").status_code == 404
    assert client.get("/api/art/cs2/pas-un-type").status_code == 404
