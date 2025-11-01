import ipaddress
from unittest.mock import MagicMock

from starlette.datastructures import Headers

from fastapi_ipware import FastAPIIpWare


def create_mock_request(headers_dict):
    """Helper to create a mock Request object with specified headers."""
    request = MagicMock()
    request.headers = Headers(headers_dict)
    return request


class TestBasicFunctionality:
    """Test basic IP extraction without proxy configuration."""

    def test_simple_forwarded_for(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is False

    def test_multiple_ips_leftmost(self):
        ipware = FastAPIIpWare(leftmost=True)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1, 9.9.9.9"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_multiple_ips_rightmost(self):
        ipware = FastAPIIpWare(leftmost=False)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1, 9.9.9.9"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("9.9.9.9")

    def test_ipv6_address(self):
        ipware = FastAPIIpWare()
        request = create_mock_request({"X-Forwarded-For": "2001:db8::1"})

        ip, trusted = ipware.get_client_ip_from_request(request)

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

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip is None


class TestPrecedence:
    """Test header precedence order."""

    def test_default_precedence(self):
        # X-Forwarded-For should take precedence over X-Real-IP by default
        ipware = FastAPIIpWare()
        request = create_mock_request(
            {"X-Forwarded-For": "8.8.8.8", "X-Real-IP": "1.1.1.1"}
        )

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_custom_precedence(self):
        # Put X-Real-IP first in custom precedence
        ipware = FastAPIIpWare(precedence=("X-Real-IP", "X-Forwarded-For"))
        request = create_mock_request(
            {"X-Forwarded-For": "8.8.8.8", "X-Real-IP": "1.1.1.1"}
        )

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("1.1.1.1")

    def test_cloudflare_precedence(self):
        ipware = FastAPIIpWare(precedence=("CF-Connecting-IP", "X-Forwarded-For"))
        request = create_mock_request(
            {"CF-Connecting-IP": "8.8.8.8", "X-Forwarded-For": "1.1.1.1"}
        )

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

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
    """Test proxy count validation."""

    def test_proxy_count_zero(self):
        # No proxies expected, just client
        ipware = FastAPIIpWare(proxy_count=0)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8"})

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True  # proxy_count is set, so trusted

    def test_proxy_count_one_non_strict(self):
        # At least 1 proxy expected
        ipware = FastAPIIpWare(proxy_count=1)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=False)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_proxy_count_one_strict_match(self):
        # Exactly 1 proxy expected
        ipware = FastAPIIpWare(proxy_count=1)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_proxy_count_strict_mismatch(self):
        # Exactly 1 proxy expected but 2 provided
        ipware = FastAPIIpWare(proxy_count=1)
        request = create_mock_request({"X-Forwarded-For": "8.8.8.8, 1.1.1.1, 9.9.9.9"})

        ip, trusted = ipware.get_client_ip_from_request(request, strict=True)

        # Should not find IP because proxy count doesn't match
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
    """Test trusted proxy list validation."""

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
        request = create_mock_request(
            {"X-Forwarded-For": "8.8.8.8, 9.9.9.9"}  # Wrong proxy
        )

        ip, trusted = ipware.get_client_ip_from_request(request)

        # Should not find IP because proxy is not trusted
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

        # Should not find IP because there's an extra proxy
        assert ip is None
        assert trusted is False


class TestProxyCountAndList:
    """Test combination of proxy count and proxy list."""

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

        # Count doesn't match (expected 1, got 2)
        assert ip is None
        assert trusted is False


class TestIPTypes:
    """Test different IP address types (public, private, loopback)."""

    def test_public_ip_preferred(self):
        ipware = FastAPIIpWare()
        request = create_mock_request(
            {"X-Forwarded-For": "8.8.8.8"}  # Public IP (Google DNS)
        )

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

    def test_public_preferred_over_private(self):
        # ipware returns first valid IP based on precedence, then filters by type
        # It will check X-Real-IP first (private), skip it internally,
        # then check X-Forwarded-For (public) and return it
        ipware = FastAPIIpWare(precedence=("X-Real-IP", "X-Forwarded-For"))
        request = create_mock_request(
            {"X-Real-IP": "192.168.1.1", "X-Forwarded-For": "8.8.8.8"}
        )

        ip, _ = ipware.get_client_ip_from_request(request)

        # ipware prefers public IPs - will find public even if private has higher precedence
        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert ip is not None
        assert ip.is_global


class TestIPWithPort:
    """Test IP addresses that include port numbers."""

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
    """Test real-world deployment scenarios."""

    def test_aws_alb_scenario(self):
        # AWS ALB typically adds X-Forwarded-For
        ipware = FastAPIIpWare(proxy_count=1, proxy_list=["10.0."])
        request = create_mock_request(
            {"X-Forwarded-For": "8.8.8.8, 10.0.1.1"}  # Client  # ALB internal IP
        )

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True

    def test_cloudflare_scenario(self):
        # Cloudflare provides CF-Connecting-IP
        ipware = FastAPIIpWare(precedence=("CF-Connecting-IP",))
        request = create_mock_request(
            {"CF-Connecting-IP": "8.8.8.8", "X-Forwarded-For": "1.1.1.1"}
        )

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_nginx_scenario(self):
        # NGINX typically uses X-Real-IP
        ipware = FastAPIIpWare(precedence=("X-Real-IP", "X-Forwarded-For"))
        request = create_mock_request({"X-Real-IP": "8.8.8.8"})

        ip, _ = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")

    def test_multiple_proxies_scenario(self):
        # Client -> CDN -> Load Balancer -> Server
        ipware = FastAPIIpWare(proxy_count=2, proxy_list=["10.1.", "10.2."])
        request = create_mock_request(
            {
                "X-Forwarded-For": "8.8.8.8, 10.1.1.1, 10.2.2.2"  # Client  # CDN  # LB
            }
        )

        ip, trusted = ipware.get_client_ip_from_request(request)

        assert ip == ipaddress.IPv4Address("8.8.8.8")
        assert trusted is True
