import ipaddress
from unittest.mock import MagicMock

from starlette.datastructures import Headers

from fastapi_ipware import FastAPIIpWare


def create_mock_request(
    headers_dict: dict[str, str], client_host: str | None = None
) -> MagicMock:
    "Helper to create a mock Request object with specified headers"
    request = MagicMock()
    request.headers = Headers(headers_dict)
    request.client = None

    if client_host:
        request.client = MagicMock(host=client_host)

    return request


class TestBasicFunctionality:
    "Test basic IP extraction without proxy configuration"

    def test_simple_forwarded_for(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is False

    def test_multiple_ips_leftmost(self):
        ipware = FastAPIIpWare(leftmost=True)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1, 9.9.9.9"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_multiple_ips_rightmost(self):
        ipware = FastAPIIpWare(leftmost=False)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1, 9.9.9.9"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("9.9.9.9")

    def test_ipv6_address(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "2001:db8::1"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv6Address("2001:db8::1")

    def test_no_ip_found(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip is None
        assert trusted is False

    def test_invalid_ip_ignored(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "invalid-ip"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip is None


class TestPrecedence:
    "Test header precedence order"

    def test_default_precedence(self):
        # x-forwarded-for should take precedence over x-real-ip by default
        ipware = FastAPIIpWare()
        request = create_mock_request(
            {"X-Forwarded-For": "8.8.8.8", "X-Real-IP": "1.1.1.1"}
        )

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_custom_precedence(self):
        # put x-real-ip first in custom precedence
        ipware = FastAPIIpWare(precedence=("X-Real-IP", "X-Forwarded-For"))
        request = create_mock_request(
            {"X-Forwarded-For": "8.8.8.8", "X-Real-IP": "1.1.1.1"}
        )

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("1.1.1.1")

    def test_cloudflare_precedence(self):
        ipware = FastAPIIpWare(precedence=("CF-Connecting-IP", "X-Forwarded-For"))
        request = create_mock_request(
            {"CF-Connecting-IP": "8.8.8.8", "X-Forwarded-For": "1.1.1.1"}
        )

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_cloudflare_used_when_no_xff(self):
        ipware = FastAPIIpWare(precedence=("CF-Connecting-IP", "X-Forwarded-For"))
        request = create_mock_request({"CF-Connecting-IP": "198.51.100.42"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("198.51.100.42")

    def test_provider_header_precedence_over_generic(self):
        ipware = FastAPIIpWare()
        request = create_mock_request(
            {
                "X-Forwarded-For": "1.1.1.1",
                "CF-Connecting-IP": "8.8.8.8",
            }
        )

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")


class TestProxyCount:
    "Test proxy count validation"

    def test_proxy_count_zero(self):
        # no proxies expected, just client
        ipware = FastAPIIpWare(proxy_count=0)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        # proxy_count is set, so trusted
        assert trusted is True

    def test_proxy_count_one_non_strict(self):
        # at least 1 proxy expected
        ipware = FastAPIIpWare(proxy_count=1)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=False)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_proxy_count_one_strict_match(self):
        # exactly 1 proxy expected
        ipware = FastAPIIpWare(proxy_count=1)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_proxy_count_strict_mismatch(self):
        # exactly 1 proxy expected but 2 provided
        ipware = FastAPIIpWare(proxy_count=1)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1, 9.9.9.9"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

        # should not find ip because proxy count doesn't match
        assert ip is None
        assert trusted is False

    def test_proxy_count_insufficient(self):
        # 2 proxies expected but only 1 provided
        ipware = FastAPIIpWare(proxy_count=2)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=False)

        assert ip is None
        assert trusted is False


class TestProxyList:
    "Test trusted proxy list validation"

    def test_proxy_list_single_trusted(self):
        ipware = FastAPIIpWare(proxy_list=["1.1.1."])
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_proxy_list_multiple_trusted(self):
        ipware = FastAPIIpWare(proxy_list=["1.1.1.", "9.9.9."])
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1, 9.9.9.9"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_proxy_list_untrusted(self):
        ipware = FastAPIIpWare(proxy_list=["1.1.1."])
        # wrong proxy
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 9.9.9.9"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        # should not find ip because proxy is not trusted
        assert ip is None
        assert trusted is False

    def test_proxy_list_strict_match(self):
        ipware = FastAPIIpWare(proxy_list=["1.1.1."])
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_proxy_list_strict_extra_proxy(self):
        ipware = FastAPIIpWare(proxy_list=["1.1.1."])
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 9.9.9.9, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

        # should not find ip because there's an extra proxy
        assert ip is None
        assert trusted is False


class TestProxyCountAndList:
    "Test combination of proxy count and proxy list"

    def test_combined_validation(self):
        ipware = FastAPIIpWare(proxy_count=1, proxy_list=["1.1.1."])
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_combined_count_mismatch(self):
        ipware = FastAPIIpWare(proxy_count=1, proxy_list=["1.1.1."])
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 9.9.9.9, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

        # count doesn't match (expected 1, got 2)
        assert ip is None
        assert trusted is False


class TestIPTypes:
    "Test different IP address types (public, private, loopback)"

    def test_public_ip_preferred(self):
        ipware = FastAPIIpWare()
        # public ip (google dns)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert ip is not None
        assert ip.is_global

    def test_private_ip_fallback(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "192.168.1.1"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("192.168.1.1")
        assert ip is not None
        assert ip.is_private

    def test_loopback_ip(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "127.0.0.1"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("127.0.0.1")
        assert ip is not None
        assert ip.is_loopback


class TestClientHostFallback:
    "Test fallback to client host when no headers are present"

    def test_fallback_to_client_host_ipv4(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({}, client_host="198.51.100.23")

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("198.51.100.23")

    def test_public_preferred_over_private(self):
        # ipware returns first valid ip based on precedence, then filters by type
        # it will check x-real-ip first (private), skip it internally
        # then check x-forwarded-for (public) and return it
        ipware = FastAPIIpWare(precedence=("X-Real-IP", "X-Forwarded-For"))
        request = create_mock_request(
            {"X-Real-IP": "192.168.1.1", "X-Forwarded-For": "8.8.8.8"}
        )

        ip, _ = ipware.get_client_ip_from_request(request)

        # ipware prefers public ips - will find public even if private has higher precedence
        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert ip is not None
        assert ip.is_global


class TestIPWithPort:
    "Test IP addresses that include port numbers"

    def test_ipv4_with_port(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "203.0.113.1:8080"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("203.0.113.1")

    def test_ipv6_with_port(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "[2001:db8::1]:8080"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv6Address("2001:db8::1")


class TestRealWorldScenarios:
    "Test real-world deployment scenarios"

    def test_aws_alb_scenario(self):
        # aws alb typically adds x-forwarded-for
        ipware = FastAPIIpWare(proxy_count=1, proxy_list=["10.0."])
        # client
        # alb internal ip
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 10.0.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_cloudflare_scenario(self):
        # cloudflare provides cf-connecting-ip
        ipware = FastAPIIpWare(precedence=("CF-Connecting-IP",))
        request = create_mock_request(
            {"CF-Connecting-IP": "8.8.8.8", "X-Forwarded-For": "1.1.1.1"}
        )

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_nginx_scenario(self):
        # nginx typically uses x-real-ip
        ipware = FastAPIIpWare(precedence=("X-Real-IP", "X-Forwarded-For"))
        request = create_mock_request({"X-Real-IP": "8.8.8.8"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_multiple_proxies_scenario(self):
        # client -> cdn -> load balancer -> server
        ipware = FastAPIIpWare(proxy_count=2, proxy_list=["10.1.", "10.2."])
        # client
        # cdn
        # lb
        request = create_mock_request(
            {"X-Forwarded-For": "8.8.8.8, 10.1.1.1, 10.2.2.2"}
        )

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True


class TestIpwareV4Features:
    "Test features and compatibility introduced in python-ipware 4.x"

    def test_rfc7239_forwarded_for_parameter(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"Forwarded": 'for="198.51.100.1";proto=https'})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("198.51.100.1")

    def test_new_edge_headers(self):
        for header_name in (
            "Fly-Client-IP",
            "X-Azure-ClientIP",
            "DO-Connecting-IP",
            "X-Envoy-External-Address",
        ):
            ipware = FastAPIIpWare()
            request = create_mock_request({header_name: "198.51.100.2"})

            ip, _ = ipware.get_client_ip_from_request(request)

            assert ip == ipaddress.IPv4Address("198.51.100.2"), (
                f"Failed for {header_name}"
            )

    def test_cidr_network_proxy_list(self):
        ipware = FastAPIIpWare(proxy_count=1, proxy_list=["100.64.0.0/10"])
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 100.64.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_algorithm_selection(self):
        ipware_modern = FastAPIIpWare(algorithm="modern")
        assert ipware_modern.algorithm == "modern"

        ipware_legacy = FastAPIIpWare(algorithm="legacy")
        assert ipware_legacy.algorithm == "legacy"

        ipware_auto = FastAPIIpWare(algorithm="auto")
        assert ipware_auto.algorithm == "auto"

    def test_property_accessors(self):
        ipware = FastAPIIpWare(
            precedence=("CF-Connecting-IP", "X-Forwarded-For"),
            leftmost=False,
            proxy_count=2,
            proxy_list=["10.0.0.0/8"],
        )

        assert isinstance(ipware.precedence, tuple)
        assert "CF-Connecting-IP" in ipware.precedence
        assert ipware.leftmost is False
        assert ipware.proxy_count == 2
        assert ipware.proxy_list == ["10.0.0.0/8"]

    def test_direct_get_client_ip_with_various_header_formats(self):
        ipware = FastAPIIpWare(
            precedence=("HTTP_X_REAL_IP", "CF-Connecting-IP", "X-Forwarded-For")
        )

        # natural header format
        ip1, _ = ipware.get_client_ip({"X-Forwarded-For": "8.8.8.8"})
        assert ip1 == ipaddress.IPv4Address("8.8.8.8")

        # lowercase header format
        ip2, _ = ipware.get_client_ip({"x-forwarded-for": "8.8.8.8"})
        assert ip2 == ipaddress.IPv4Address("8.8.8.8")

        # wsgi format
        ip3, _ = ipware.get_client_ip({"HTTP_X_FORWARDED_FOR": "8.8.8.8"})
        assert ip3 == ipaddress.IPv4Address("8.8.8.8")

        # custom precedence with http_ prefix provided by user
        ip4, _ = ipware.get_client_ip(
            {"x-real-ip": "1.1.1.1", "cf-connecting-ip": "2.2.2.2"}
        )
        assert ip4 == ipaddress.IPv4Address("1.1.1.1")
