import ipaddress
import re
import httpx

NETPULSE_BASE = "http://localhost:8000"


def get_devices() -> dict:
    try:
        r = httpx.get(f"{NETPULSE_BASE}/api/devices", timeout=5.0)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": "NetPulse is not running (http://localhost:8000). Start it first."}
    except Exception as e:
        return {"error": str(e)}


def get_device_history(ip: str) -> dict:
    try:
        r = httpx.get(f"{NETPULSE_BASE}/api/devices/{ip}/history", timeout=5.0)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": "NetPulse is not running (http://localhost:8000). Start it first."}
    except Exception as e:
        return {"error": str(e)}


def plan_subnets(base_cidr: str, requirements: list[dict]) -> dict:
    """VLSM allocation: largest-first, power-of-2 sizing, hosts+2."""
    try:
        network = ipaddress.ip_network(base_cidr, strict=False)
    except ValueError as e:
        return {"error": f"Invalid base CIDR: {e}"}

    sorted_reqs = sorted(requirements, key=lambda r: r["hosts"], reverse=True)
    allocations = []
    current_int = int(network.network_address)

    for req in sorted_reqs:
        needed = req["hosts"] + 2
        prefix_len = 32
        while (2 ** (32 - prefix_len)) < needed:
            prefix_len -= 1

        block_size = 2 ** (32 - prefix_len)
        remainder = current_int % block_size
        if remainder != 0:
            current_int += block_size - remainder

        try:
            subnet = ipaddress.ip_network(f"{ipaddress.ip_address(current_int)}/{prefix_len}")
        except ValueError as e:
            return {"error": f"Address calculation failed for '{req['name']}': {e}"}

        if not subnet.subnet_of(network):
            return {"error": f"Address space exhausted when allocating '{req['name']}'"}

        allocations.append({
            "name": req["name"],
            "hosts_requested": req["hosts"],
            "subnet": str(subnet),
            "network": str(subnet.network_address),
            "broadcast": str(subnet.broadcast_address),
            "first_host": str(subnet.network_address + 1),
            "last_host": str(subnet.broadcast_address - 1),
            "usable_hosts": subnet.num_addresses - 2,
            "prefix_length": prefix_len,
        })
        current_int = int(subnet.broadcast_address) + 1

    return {"base_cidr": base_cidr, "allocations": allocations}


def _vty_allows_telnet(transport_input: str | None) -> bool:
    if transport_input is None:
        return True  # IOS default allows all transports including telnet
    return "telnet" in transport_input or "all" in transport_input


def audit_config(config_text: str) -> dict:
    findings = []
    lines = [l.strip() for l in config_text.splitlines()]

    # service password-encryption
    if not any(l == "service password-encryption" for l in lines):
        findings.append({
            "severity": "MEDIUM",
            "issue": "service password-encryption is not configured",
            "remediation": "service password-encryption",
        })

    # enable secret vs enable password
    has_enable_secret = any(re.match(r"enable secret \S+", l) for l in lines)
    has_enable_password = any(re.match(r"enable password \S+", l) for l in lines)
    if not has_enable_secret:
        if has_enable_password:
            findings.append({
                "severity": "HIGH",
                "issue": "enable password used instead of enable secret (plaintext/reversible)",
                "remediation": "no enable password\nenable secret <strong-password>",
            })
        else:
            findings.append({
                "severity": "HIGH",
                "issue": "No enable secret configured",
                "remediation": "enable secret <strong-password>",
            })

    # plaintext passwords in line/username context
    plaintext_pw = re.compile(r"^(password \S+|username \S+ password \S+)$")
    for l in lines:
        if plaintext_pw.match(l):
            findings.append({
                "severity": "HIGH",
                "issue": f"Plaintext password: {l}",
                "remediation": "Use 'secret' instead of 'password', or enable service password-encryption",
            })

    # ip http server (unencrypted HTTP management)
    if any(l == "ip http server" for l in lines) and not any(l == "no ip http server" for l in lines):
        findings.append({
            "severity": "HIGH",
            "issue": "ip http server enabled (unencrypted HTTP management interface)",
            "remediation": "no ip http server\nip http secure-server",
        })

    # VTY section analysis
    in_vty = False
    vty_transport_input = None
    vty_has_access_class = False

    def flush_vty():
        nonlocal in_vty, vty_transport_input, vty_has_access_class
        if not in_vty:
            return
        if _vty_allows_telnet(vty_transport_input):
            findings.append({
                "severity": "HIGH",
                "issue": "Telnet allowed on VTY lines (not restricted to SSH)",
                "remediation": "transport input ssh",
            })
        if not vty_has_access_class:
            findings.append({
                "severity": "MEDIUM",
                "issue": "No access-class configured on VTY lines",
                "remediation": "access-class <ACL_NUMBER> in",
            })
        in_vty = False
        vty_transport_input = None
        vty_has_access_class = False

    section_start = re.compile(r"^(interface |router |line |ip route |crypto |banner )")

    for l in lines:
        if l.startswith("line vty"):
            flush_vty()
            in_vty = True
        elif in_vty and (section_start.match(l) or l == "!"):
            flush_vty()

        if in_vty:
            m = re.match(r"transport input (.+)", l)
            if m:
                vty_transport_input = m.group(1)
            if l.startswith("access-class"):
                vty_has_access_class = True

    flush_vty()

    return {
        "findings": findings,
        "summary": f"{len(findings)} issue(s) found",
        "severities": {
            "HIGH": sum(1 for f in findings if f["severity"] == "HIGH"),
            "MEDIUM": sum(1 for f in findings if f["severity"] == "MEDIUM"),
            "LOW": sum(1 for f in findings if f["severity"] == "LOW"),
        },
    }
