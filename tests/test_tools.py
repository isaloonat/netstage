import json
from unittest.mock import MagicMock, patch

import pytest

from backend.tools import audit_config, get_device_history, get_devices, plan_subnets


# ---------------------------------------------------------------------------
# plan_subnets
# ---------------------------------------------------------------------------

class TestPlanSubnets:
    def test_basic_allocation(self):
        result = plan_subnets(
            "192.168.1.0/24",
            [
                {"name": "Staff", "hosts": 60},
                {"name": "Students", "hosts": 100},
                {"name": "IoT", "hosts": 20},
            ],
        )
        assert "allocations" in result
        allocs = {a["name"]: a for a in result["allocations"]}

        # Largest first: Students(100) → /25, Staff(60) → /26, IoT(20) → /27
        assert allocs["Students"]["subnet"] == "192.168.1.0/25"
        assert allocs["Students"]["usable_hosts"] == 126
        assert allocs["Staff"]["subnet"] == "192.168.1.128/26"
        assert allocs["Staff"]["usable_hosts"] == 62
        assert allocs["IoT"]["subnet"] == "192.168.1.192/27"
        assert allocs["IoT"]["usable_hosts"] == 30

    def test_hosts_plus_two(self):
        result = plan_subnets("10.0.0.0/24", [{"name": "Tiny", "hosts": 2}])
        assert "allocations" in result
        # 2 hosts + 2 = 4 → /30
        assert result["allocations"][0]["subnet"] == "10.0.0.0/30"
        assert result["allocations"][0]["usable_hosts"] == 2

    def test_single_host(self):
        result = plan_subnets("10.0.0.0/24", [{"name": "Mgmt", "hosts": 1}])
        assert "allocations" in result
        # 1 host + 2 = 3 → /30 (4 addresses)
        assert result["allocations"][0]["subnet"] == "10.0.0.0/30"

    def test_address_exhaustion(self):
        result = plan_subnets("192.168.1.0/30", [{"name": "Big", "hosts": 100}])
        assert "error" in result
        assert "exhausted" in result["error"].lower() or "Invalid" in result["error"]

    def test_invalid_cidr(self):
        result = plan_subnets("not-a-cidr", [{"name": "X", "hosts": 10}])
        assert "error" in result

    def test_multiple_subnets_no_overlap(self):
        result = plan_subnets(
            "10.0.0.0/16",
            [{"name": "A", "hosts": 50}, {"name": "B", "hosts": 50}, {"name": "C", "hosts": 50}],
        )
        assert "allocations" in result
        allocs = result["allocations"]
        assert len(allocs) == 3
        # Verify no address range overlaps
        import ipaddress
        nets = [ipaddress.ip_network(a["subnet"]) for a in allocs]
        for i, n1 in enumerate(nets):
            for j, n2 in enumerate(nets):
                if i != j:
                    assert not n1.overlaps(n2), f"{n1} overlaps {n2}"

    def test_base_cidr_preserved(self):
        result = plan_subnets("172.16.0.0/24", [{"name": "X", "hosts": 10}])
        assert result["base_cidr"] == "172.16.0.0/24"

    def test_first_and_last_host(self):
        result = plan_subnets("10.0.0.0/24", [{"name": "Net", "hosts": 10}])
        alloc = result["allocations"][0]
        assert alloc["first_host"] != alloc["network"]
        assert alloc["last_host"] != alloc["broadcast"]


# ---------------------------------------------------------------------------
# audit_config
# ---------------------------------------------------------------------------

CLEAN_CONFIG = """\
service password-encryption
!
enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0
!
username admin secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0
!
line vty 0 4
 transport input ssh
 access-class 10 in
!
"""

INSECURE_CONFIG = """\
enable password cisco
!
line vty 0 4
 transport input telnet
!
ip http server
"""


class TestAuditConfig:
    def test_clean_config_no_findings(self):
        result = audit_config(CLEAN_CONFIG)
        assert result["severities"]["HIGH"] == 0
        assert result["severities"]["MEDIUM"] == 0

    def test_detects_telnet_on_vty(self):
        result = audit_config(INSECURE_CONFIG)
        issues = [f["issue"] for f in result["findings"]]
        assert any("telnet" in i.lower() or "Telnet" in i for i in issues)

    def test_detects_enable_password_not_secret(self):
        result = audit_config(INSECURE_CONFIG)
        issues = [f["issue"] for f in result["findings"]]
        assert any("enable" in i.lower() and "secret" in i.lower() for i in issues)

    def test_detects_missing_service_password_encryption(self):
        result = audit_config(INSECURE_CONFIG)
        issues = [f["issue"] for f in result["findings"]]
        assert any("password-encryption" in i for i in issues)

    def test_detects_ip_http_server(self):
        result = audit_config(INSECURE_CONFIG)
        issues = [f["issue"] for f in result["findings"]]
        assert any("http server" in i.lower() for i in issues)

    def test_detects_missing_access_class(self):
        config = "service password-encryption\nenable secret 5 abc\nline vty 0 4\n transport input ssh\n"
        result = audit_config(config)
        issues = [f["issue"] for f in result["findings"]]
        assert any("access-class" in i for i in issues)

    def test_detects_plaintext_password(self):
        config = "service password-encryption\nenable secret 5 abc\npassword cisco\nline vty 0 4\n transport input ssh\n access-class 10 in\n"
        result = audit_config(config)
        issues = [f["issue"] for f in result["findings"]]
        assert any("plaintext" in i.lower() or "Plaintext" in i for i in issues)

    def test_no_enable_secret_no_password(self):
        config = "service password-encryption\nline vty 0 4\n transport input ssh\n access-class 10 in\n"
        result = audit_config(config)
        issues = [f["issue"] for f in result["findings"]]
        assert any("enable secret" in i.lower() or "No enable secret" in i for i in issues)

    def test_no_http_server_when_explicitly_disabled(self):
        config = "service password-encryption\nenable secret 5 abc\nno ip http server\nline vty 0 4\n transport input ssh\n access-class 10 in\n"
        result = audit_config(config)
        issues = [f["issue"] for f in result["findings"]]
        assert not any("http server" in i.lower() for i in issues)

    def test_summary_string(self):
        result = audit_config(INSECURE_CONFIG)
        assert "issue" in result["summary"]

    def test_severity_counts_match_findings(self):
        result = audit_config(INSECURE_CONFIG)
        total = sum(result["severities"].values())
        assert total == len(result["findings"])

    def test_vty_transport_input_ssh_only(self):
        config = (
            "service password-encryption\n"
            "enable secret 5 abc\n"
            "line vty 0 4\n"
            " transport input ssh\n"
            " access-class 10 in\n"
        )
        result = audit_config(config)
        issues = [f["issue"] for f in result["findings"]]
        assert not any("telnet" in i.lower() for i in issues)

    def test_vty_transport_input_all_flagged(self):
        config = (
            "service password-encryption\n"
            "enable secret 5 abc\n"
            "line vty 0 4\n"
            " transport input all\n"
            " access-class 10 in\n"
        )
        result = audit_config(config)
        issues = [f["issue"] for f in result["findings"]]
        assert any("telnet" in i.lower() or "Telnet" in i for i in issues)


# ---------------------------------------------------------------------------
# get_devices (mocked HTTP)
# ---------------------------------------------------------------------------

class TestGetDevices:
    def test_returns_device_list_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = [{"ip": "10.0.0.1", "status": "up"}]
        mock_response.raise_for_status.return_value = None

        with patch("backend.tools.httpx.get", return_value=mock_response) as mock_get:
            result = get_devices()
            mock_get.assert_called_once_with("http://localhost:8000/api/devices", timeout=5.0)

        assert result == [{"ip": "10.0.0.1", "status": "up"}]

    def test_returns_error_when_netpulse_down(self):
        import httpx as _httpx

        with patch("backend.tools.httpx.get", side_effect=_httpx.ConnectError("refused")):
            result = get_devices()

        assert "error" in result
        assert "NetPulse" in result["error"]

    def test_returns_error_on_http_error(self):
        import httpx as _httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )

        with patch("backend.tools.httpx.get", return_value=mock_response):
            result = get_devices()

        assert "error" in result


# ---------------------------------------------------------------------------
# get_device_history (mocked HTTP)
# ---------------------------------------------------------------------------

class TestGetDeviceHistory:
    def test_returns_history_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ip": "10.0.0.1", "history": []}
        mock_response.raise_for_status.return_value = None

        with patch("backend.tools.httpx.get", return_value=mock_response) as mock_get:
            result = get_device_history("10.0.0.1")
            mock_get.assert_called_once_with(
                "http://localhost:8000/api/devices/10.0.0.1/history", timeout=5.0
            )

        assert result == {"ip": "10.0.0.1", "history": []}

    def test_returns_error_when_netpulse_down(self):
        import httpx as _httpx

        with patch("backend.tools.httpx.get", side_effect=_httpx.ConnectError("refused")):
            result = get_device_history("10.0.0.1")

        assert "error" in result
        assert "NetPulse" in result["error"]

    def test_returns_error_on_http_error(self):
        import httpx as _httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )

        with patch("backend.tools.httpx.get", return_value=mock_response):
            result = get_device_history("10.0.0.2")

        assert "error" in result
