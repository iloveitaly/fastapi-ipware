from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from fastapi_ipware import FastAPIIpWare


def create_app(precedence: tuple[str, ...] | None = None) -> FastAPI:
    ipware = FastAPIIpWare(precedence=precedence)
    app = FastAPI()

    @app.get("/")
    def index(request: Request) -> dict[str, str | bool | None]:
        ip, trusted = ipware.get_client_ip_from_request(request)

        return {
            "ip": str(ip) if ip else None,
            "trusted": trusted,
        }

    return app


def test_fastapi_request_x_forwarded_for() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/", headers={"X-Forwarded-For": "203.0.113.5"})

    assert response.json()["ip"] == "203.0.113.5"


def test_fastapi_request_cf_connecting_ip() -> None:
    app = create_app(precedence=("CF-Connecting-IP", "X-Forwarded-For"))
    client = TestClient(app)

    response = client.get("/", headers={"CF-Connecting-IP": "198.51.100.42"})

    assert response.json()["ip"] == "198.51.100.42"


def test_fastapi_request_custom_client_ip() -> None:
    app = create_app()
    client = TestClient(app, client=("198.51.100.23", 5150))

    response = client.get("/")

    assert response.json()["ip"] == "198.51.100.23"
