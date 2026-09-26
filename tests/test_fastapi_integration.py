from typing import Annotated

from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.testclient import TestClient

from fastapi_ipware import (
    ClientIpResult,
    FastAPIIpWare,
    IpAddressType,
    IpWareMiddleware,
)


def format_client_ip_payload(client: ClientIpResult) -> dict[str, str | bool | None]:
    "serialize client ip result into dictionary payload"
    ip, trusted = client

    return {
        "ip": str(ip) if ip is not None else None,
        "trusted": trusted,
    }


def create_app(precedence: tuple[str, ...] | None = None) -> FastAPI:
    "create test fastapi app with index endpoint returning client ip"
    ipware = FastAPIIpWare(precedence=precedence)
    app = FastAPI()

    @app.get("/")
    def index(request: Request) -> dict[str, str | bool | None]:
        client = ipware.get_client_ip_from_request(request)

        return format_client_ip_payload(client)

    return app


def create_middleware_app(
    ipware: FastAPIIpWare | None = None,
    strict: bool | None = None,
) -> FastAPI:
    "create fastapi app with ipware middleware and state inspection endpoint"
    app = FastAPI()
    app.add_middleware(IpWareMiddleware, ipware=ipware, strict=strict)

    @app.get("/state")
    def state_endpoint(request: Request) -> dict[str, str | bool | None]:
        ip = request.state.client_ip

        return {
            "ip": str(ip) if ip is not None else None,
            "trusted": request.state.ip_trusted,
            "ip_str": request.state.client_ip_str,
        }

    return app


def test_fastapi_request_x_forwarded_for():
    app = create_app()
    client = TestClient(app)

    response = client.get("/", headers={"X-Forwarded-For": "203.0.113.5"})

    assert response.json()["ip"] == "203.0.113.5"


def test_fastapi_request_cf_connecting_ip():
    app = create_app(precedence=("CF-Connecting-IP", "X-Forwarded-For"))
    client = TestClient(app)

    response = client.get("/", headers={"CF-Connecting-IP": "198.51.100.42"})

    assert response.json()["ip"] == "198.51.100.42"


def test_fastapi_request_custom_client_ip():
    app = create_app()
    client = TestClient(app, client=("198.51.100.23", 5_150))

    response = client.get("/")

    assert response.json()["ip"] == "198.51.100.23"


def test_fastapi_depends_injection():
    ipware = FastAPIIpWare()
    strict_dep = ipware.dependency(strict=True)
    app = FastAPI()

    @app.get("/client")
    def get_client(
        client: Annotated[ClientIpResult, Depends(ipware)],
    ) -> dict[str, str | bool | None]:
        return format_client_ip_payload(client)

    @app.get("/ip-only")
    def get_only_ip(
        ip: Annotated[IpAddressType | None, Depends(ipware.get_ip)],
    ) -> dict[str, str | None]:
        return {"ip": str(ip) if ip is not None else None}

    @app.get("/ip-str")
    def get_only_ip_str(
        ip_str: Annotated[str | None, Depends(ipware.get_ip_str)],
    ) -> dict[str, str | None]:
        return {"ip": ip_str}

    @app.get("/strict-dep")
    def get_strict(
        client: Annotated[ClientIpResult, Depends(strict_dep)],
    ) -> dict[str, str | bool | None]:
        return format_client_ip_payload(client)

    client = TestClient(app)
    headers = {"X-Forwarded-For": "203.0.113.10"}

    res1 = client.get("/client", headers=headers)
    assert res1.json() == {"ip": "203.0.113.10", "trusted": False}

    res2 = client.get("/ip-only", headers=headers)
    assert res2.json() == {"ip": "203.0.113.10"}

    res3 = client.get("/ip-str", headers=headers)
    assert res3.json() == {"ip": "203.0.113.10"}

    res4 = client.get("/strict-dep", headers=headers)
    assert res4.json() == {"ip": "203.0.113.10", "trusted": False}


def test_ipware_middleware_http():
    app = create_middleware_app()
    client = TestClient(app)

    res = client.get("/state", headers={"X-Forwarded-For": "203.0.113.25"})

    assert res.json() == {
        "ip": "203.0.113.25",
        "trusted": False,
        "ip_str": "203.0.113.25",
    }


def test_ipware_middleware_websocket():
    app = FastAPI()
    app.add_middleware(IpWareMiddleware)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        ip = websocket.state.client_ip
        payload = {
            "ip": str(ip) if ip is not None else None,
            "trusted": websocket.state.ip_trusted,
            "ip_str": websocket.state.client_ip_str,
        }

        await websocket.send_json(payload)
        await websocket.close()

    client = TestClient(app)

    with client.websocket_connect(
        "/ws", headers={"X-Forwarded-For": "203.0.113.50"}
    ) as ws:
        data = ws.receive_json()

        assert data == {
            "ip": "203.0.113.50",
            "trusted": False,
            "ip_str": "203.0.113.50",
        }


# two proxies on the right of the client. proxy_count=1 is a strict mismatch
MISMATCHED_FORWARDED_FOR = {"X-Forwarded-For": "203.0.113.10, 10.0.0.1, 10.0.0.2"}


def test_depends_honors_default_strict():
    ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
    loose = ipware.dependency(strict=False)
    app = FastAPI()

    @app.get("/client")
    def get_client(
        client: Annotated[ClientIpResult, Depends(ipware)],
    ) -> dict[str, str | bool | None]:
        return format_client_ip_payload(client)

    @app.get("/factory")
    def get_factory(
        client: Annotated[ClientIpResult, Depends(ipware.dependency())],
    ) -> dict[str, str | bool | None]:
        return format_client_ip_payload(client)

    @app.get("/loose")
    def get_loose(
        client: Annotated[ClientIpResult, Depends(loose)],
    ) -> dict[str, str | bool | None]:
        return format_client_ip_payload(client)

    client = TestClient(app)

    client_res = client.get("/client", headers=MISMATCHED_FORWARDED_FOR)
    assert client_res.json() == {"ip": None, "trusted": False}

    factory_res = client.get("/factory", headers=MISMATCHED_FORWARDED_FOR)
    assert factory_res.json() == {"ip": None, "trusted": False}

    loose_res = client.get("/loose", headers=MISMATCHED_FORWARDED_FOR)
    assert loose_res.json() == {"ip": "10.0.0.1", "trusted": True}


def test_depends_proxy_list_honors_default_strict():
    ipware = FastAPIIpWare(proxy_list=["10.0.0."], default_strict=True)
    loose = ipware.dependency(strict=False)
    app = FastAPI()

    @app.get("/client")
    def get_client(
        client: Annotated[ClientIpResult, Depends(ipware)],
    ) -> dict[str, str | bool | None]:
        return format_client_ip_payload(client)

    @app.get("/loose")
    def get_loose(
        client: Annotated[ClientIpResult, Depends(loose)],
    ) -> dict[str, str | bool | None]:
        return format_client_ip_payload(client)

    client = TestClient(app)

    client_res = client.get("/client", headers=MISMATCHED_FORWARDED_FOR)
    assert client_res.json() == {"ip": None, "trusted": False}

    loose_res = client.get("/loose", headers=MISMATCHED_FORWARDED_FOR)
    assert loose_res.json() == {"ip": "10.0.0.1", "trusted": True}


def test_middleware_honors_default_strict():
    ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
    app = create_middleware_app(ipware=ipware)
    client = TestClient(app)

    res = client.get("/state", headers=MISMATCHED_FORWARDED_FOR)

    assert res.json() == {"ip": None, "trusted": False, "ip_str": None}


def test_middleware_strict_override():
    ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
    app = create_middleware_app(ipware=ipware, strict=False)
    client = TestClient(app)

    res = client.get("/state", headers=MISMATCHED_FORWARDED_FOR)

    assert res.json() == {
        "ip": "10.0.0.1",
        "trusted": True,
        "ip_str": "10.0.0.1",
    }


def test_middleware_proxy_list_honors_default_strict():
    ipware = FastAPIIpWare(proxy_list=["10.0.0."], default_strict=True)
    app = create_middleware_app(ipware=ipware)
    client = TestClient(app)

    res = client.get("/state", headers=MISMATCHED_FORWARDED_FOR)

    assert res.json() == {"ip": None, "trusted": False, "ip_str": None}


def test_depends_websocket():
    ipware = FastAPIIpWare(proxy_count=1, default_strict=True)
    loose = ipware.dependency(strict=False)
    app = FastAPI()

    @app.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        client: Annotated[ClientIpResult, Depends(ipware)],
    ):
        await websocket.accept()
        await websocket.send_json(format_client_ip_payload(client))
        await websocket.close()

    @app.websocket("/ws-loose")
    async def websocket_loose(
        websocket: WebSocket,
        client: Annotated[ClientIpResult, Depends(loose)],
    ):
        await websocket.accept()
        await websocket.send_json(format_client_ip_payload(client))
        await websocket.close()

    client = TestClient(app)

    with client.websocket_connect("/ws", headers=MISMATCHED_FORWARDED_FOR) as ws:
        assert ws.receive_json() == {"ip": None, "trusted": False}

    with client.websocket_connect("/ws-loose", headers=MISMATCHED_FORWARDED_FOR) as ws:
        assert ws.receive_json() == {"ip": "10.0.0.1", "trusted": True}
