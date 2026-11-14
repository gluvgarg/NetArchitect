"""Unit and Integration Tests for Configuration Generation Engine (Phase 6).

Academic Context:
Validates Cisco IOS CLI generation, IEEE 802.1Q VLAN tagging, Layer 3 addressing,
Single/Multi-Area OSPF (RFC 2328), eBGP peering (RFC 4271), safety checks against
credential exposure, duplicate interfaces/VLANs, and secure file downloads.
"""

import os
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi import HTTPException
from fastapi.responses import FileResponse

from engines.config_generator import ConfigGenerator
from engines.explainability_engine import ExplainabilityEngine
from models.config import (
    ConfigGenerationRequest,
    ConfigGenerationResponse,
    InterfaceConfig,
    VLANConfig,
    OSPFConfig,
    OSPFNetworkConfig,
    BGPConfig,
    BGPNeighborConfig,
    BGPNetworkConfig,
)
from api.routes.configs import (
    generate_config,
    get_config_by_id,
    download_config_file,
    configs_info,
)


@pytest.fixture
def explainability_engine():
    """Provides a fresh ExplainabilityEngine fixture."""
    return ExplainabilityEngine()


@pytest.fixture
def generator(tmp_path, explainability_engine):
    """Provides a ConfigGenerator instance with a temporary export directory."""
    return ConfigGenerator(
        export_dir=str(tmp_path),
        explainability_engine=explainability_engine,
    )


# ==============================================================================
# 1. Basic Device Configuration Tests (Router & Switch)
# ==============================================================================

def test_basic_router_configuration(generator):
    """Router configuration must include hostname, no ip domain-lookup, ip routing, and interfaces."""
    req = ConfigGenerationRequest(
        network_name="Campus-Core",
        hostname="R1-Core",
        device_type="router",
        device_role="core",
        interfaces=[
            InterfaceConfig(
                name="GigabitEthernet0/0/0",
                description="Uplink to Distribution",
                ip_address="10.0.0.1",
                subnet_mask="255.255.255.252",
                enabled=True,
            )
        ],
    )
    res = generator.generate_config(req)

    assert res["hostname"] == "R1-Core"
    assert res["device_type"] == "router"
    assert res["validation_status"] == "VALID"

    config_text = res["complete_config_text"]
    assert "hostname R1-Core" in config_text
    assert "no ip domain-lookup" in config_text
    assert "ip routing" in config_text
    assert "interface GigabitEthernet0/0/0" in config_text
    assert "ip address 10.0.0.1 255.255.255.252" in config_text
    assert "no shutdown" in config_text
    assert "end" in config_text

    # File export verification
    assert os.path.exists(res["export_file_path"]) or (Path(generator.export_dir) / res["export_filename"]).exists()


def test_basic_switch_configuration(generator):
    """Switch configuration must include hostname, default gateway, and omit ip routing."""
    req = ConfigGenerationRequest(
        network_name="Campus-Access",
        hostname="SW1-Access",
        device_type="switch",
        device_role="access",
        default_gateway="192.168.1.1",
        interfaces=[
            InterfaceConfig(
                name="Vlan1",
                description="Management SVI",
                ip_address="192.168.1.2",
                subnet_mask="255.255.255.0",
                enabled=True,
            )
        ],
    )
    res = generator.generate_config(req)

    assert res["hostname"] == "SW1-Access"
    assert res["device_type"] == "switch"

    config_text = res["complete_config_text"]
    assert "hostname SW1-Access" in config_text
    assert "no ip domain-lookup" in config_text
    assert "ip routing" not in config_text
    assert "ip default-gateway 192.168.1.1" in config_text
    assert "interface Vlan1" in config_text
    assert "ip address 192.168.1.2 255.255.255.0" in config_text


# ==============================================================================
# 2. VLAN Configuration & Switchport Mode Tests (IEEE 802.1Q)
# ==============================================================================

def test_vlan_creation(generator):
    """Declared VLANs must generate 802.1Q VLAN database statements."""
    req = ConfigGenerationRequest(
        network_name="Campus-Access",
        hostname="SW1-Floor1",
        device_type="switch",
        device_role="access",
        vlans=[
            VLANConfig(vlan_id=10, name="Faculty_Staff"),
            VLANConfig(vlan_id=20, name="Student_Lab"),
        ],
    )
    res = generator.generate_config(req)

    config_text = res["complete_config_text"]
    assert "vlan 10" in config_text
    assert " name Faculty_Staff" in config_text
    assert "vlan 20" in config_text
    assert " name Student_Lab" in config_text


def test_access_port_assignment(generator):
    """Access mode port must configure switchport mode access and access vlan."""
    req = ConfigGenerationRequest(
        network_name="Campus-Access",
        hostname="SW1-Access",
        device_type="switch",
        vlans=[VLANConfig(vlan_id=10, name="Workstations")],
        interfaces=[
            InterfaceConfig(
                name="FastEthernet0/1",
                description="Desk Drop Port",
                mode="access",
                access_vlan=10,
                enabled=True,
            )
        ],
    )
    res = generator.generate_config(req)

    config_text = res["complete_config_text"]
    assert "interface FastEthernet0/1" in config_text
    assert "switchport mode access" in config_text
    assert "switchport access vlan 10" in config_text
    assert "no shutdown" in config_text


def test_trunk_port_allowed_vlans(generator):
    """Trunk mode port must configure dot1q encapsulation and restricted allowed-vlan list."""
    req = ConfigGenerationRequest(
        network_name="Campus-Core",
        hostname="SW-Dist-1",
        device_type="switch",
        vlans=[
            VLANConfig(vlan_id=10, name="Voice"),
            VLANConfig(vlan_id=20, name="Data"),
            VLANConfig(vlan_id=99, name="Management"),
        ],
        interfaces=[
            InterfaceConfig(
                name="GigabitEthernet0/24",
                description="Uplink Trunk to Core",
                mode="trunk",
                allowed_vlans=[10, 20, 99],
                enabled=True,
            )
        ],
    )
    res = generator.generate_config(req)

    config_text = res["complete_config_text"]
    assert "interface GigabitEthernet0/24" in config_text
    assert "switchport trunk encapsulation dot1q" in config_text
    assert "switchport mode trunk" in config_text
    assert "switchport trunk allowed vlan 10,20,99" in config_text


# ==============================================================================
# 3. Layer 3 Addressing Tests
# ==============================================================================

def test_interface_ip_configuration(generator):
    """Layer 3 interface must correctly format IP address and subnet mask."""
    req = ConfigGenerationRequest(
        network_name="Campus-Core",
        hostname="R1-Gateway",
        device_type="router",
        interfaces=[
            InterfaceConfig(
                name="GigabitEthernet0/0/1",
                description="WAN Gateway Interface",
                ip_address="172.16.1.1",
                subnet_mask="255.255.255.0",
                media_type="Cat6a",
                enabled=True,
            )
        ],
    )
    res = generator.generate_config(req)

    config_text = res["complete_config_text"]
    assert "interface GigabitEthernet0/0/1" in config_text
    assert "description WAN Gateway Interface [Cat6a]" in config_text
    assert "ip address 172.16.1.1 255.255.255.0" in config_text
    assert "no shutdown" in config_text


# ==============================================================================
# 4. Routing Protocol Configuration Tests (OSPF & eBGP)
# ==============================================================================

def test_single_area_ospf_configuration(generator):
    """Single-Area OSPF must generate router ospf, router-id, and Area 0 network statements."""
    req = ConfigGenerationRequest(
        network_name="Campus-LAN",
        hostname="R1-Core",
        device_type="router",
        routing_architecture="Single-Area OSPF (Area 0)",
        ospf=OSPFConfig(
            process_id=1,
            router_id="1.1.1.1",
            networks=[
                OSPFNetworkConfig(network="10.0.0.0", wildcard_mask="0.0.0.3", area=0),
                OSPFNetworkConfig(network="192.168.1.0", wildcard_mask="0.0.0.255", area=0),
            ],
            passive_interfaces=["GigabitEthernet0/0/1"],
        ),
        interfaces=[
            InterfaceConfig(name="GigabitEthernet0/0/0", ip_address="10.0.0.1", subnet_mask="255.255.255.252"),
            InterfaceConfig(name="GigabitEthernet0/0/1", ip_address="192.168.1.1", subnet_mask="255.255.255.0"),
        ],
    )
    res = generator.generate_config(req)

    config_text = res["complete_config_text"]
    assert "router ospf 1" in config_text
    assert "router-id 1.1.1.1" in config_text
    assert "passive-interface GigabitEthernet0/0/1" in config_text
    assert "network 10.0.0.0 0.0.0.3 area 0" in config_text
    assert "network 192.168.1.0 0.0.0.255 area 0" in config_text


def test_multi_area_ospf_configuration(generator):
    """Multi-Area OSPF must generate backbone Area 0 and designated non-backbone areas."""
    req = ConfigGenerationRequest(
        network_name="Metro-MAN",
        hostname="ABR-Router",
        device_type="router",
        routing_architecture="Multi-Area OSPF",
        ospf=OSPFConfig(
            process_id=10,
            router_id="10.10.10.1",
            networks=[
                OSPFNetworkConfig(network="10.0.0.0", wildcard_mask="0.0.0.3", area=0),
                OSPFNetworkConfig(network="10.1.0.0", wildcard_mask="0.0.0.255", area=1),
                OSPFNetworkConfig(network="10.2.0.0", wildcard_mask="0.0.0.255", area=2),
            ],
        ),
    )
    res = generator.generate_config(req)

    config_text = res["complete_config_text"]
    assert "router ospf 10" in config_text
    assert "router-id 10.10.10.1" in config_text
    assert "network 10.0.0.0 0.0.0.3 area 0" in config_text
    assert "network 10.1.0.0 0.0.0.255 area 1" in config_text
    assert "network 10.2.0.0 0.0.0.255 area 2" in config_text


def test_ebgp_configuration(generator):
    """eBGP must configure local AS, neighbors, remote-as, and advertised prefixes."""
    req = ConfigGenerationRequest(
        network_name="Global-WAN",
        hostname="R1-Edge",
        device_type="router",
        routing_architecture="eBGP",
        bgp=BGPConfig(
            local_as=65001,
            router_id="198.51.100.2",
            neighbors=[
                BGPNeighborConfig(
                    ip_address="198.51.100.1",
                    remote_as=65000,
                    description="Peering to Upstream ISP Transit",
                )
            ],
            networks=[
                BGPNetworkConfig(network="10.0.0.0", mask="255.255.240.0")
            ],
        ),
    )
    res = generator.generate_config(req)

    config_text = res["complete_config_text"]
    assert "router bgp 65001" in config_text
    assert "bgp router-id 198.51.100.2" in config_text
    assert "neighbor 198.51.100.1 remote-as 65000" in config_text
    assert "neighbor 198.51.100.1 description Peering to Upstream ISP Transit" in config_text
    assert "network 10.0.0.0 mask 255.255.240.0" in config_text


# ==============================================================================
# 5. Input Validation & Safety Tests
# ==============================================================================

def test_invalid_ip_address_raises_validation_error():
    """Invalid IP address on interface must raise ValidationError."""
    with pytest.raises(ValidationError):
        InterfaceConfig(
            name="GigabitEthernet0/0/0",
            ip_address="999.999.999.999",
            subnet_mask="255.255.255.0",
        )


def test_duplicate_interfaces_raises_validation_error():
    """Duplicate interface names on the same device must be rejected."""
    with pytest.raises(ValidationError, match="Duplicate interface configuration detected"):
        ConfigGenerationRequest(
            hostname="R1",
            interfaces=[
                InterfaceConfig(name="GigabitEthernet0/0/0", ip_address="10.0.0.1", subnet_mask="255.255.255.0"),
                InterfaceConfig(name="gigabitethernet0/0/0", ip_address="10.0.0.2", subnet_mask="255.255.255.0"),
            ],
        )


def test_duplicate_vlan_ids_raises_validation_error():
    """Duplicate VLAN IDs on the same switch must be rejected."""
    with pytest.raises(ValidationError, match="Duplicate VLAN ID detected"):
        ConfigGenerationRequest(
            hostname="SW1",
            device_type="switch",
            vlans=[
                VLANConfig(vlan_id=10, name="Sales"),
                VLANConfig(vlan_id=10, name="Marketing"),
            ],
        )


def test_undeclared_access_vlan_assignment_raises_validation_error():
    """Assigning an interface to a VLAN not declared on the switch must be rejected."""
    with pytest.raises(ValidationError, match="is assigned access VLAN 50, which is not among"):
        ConfigGenerationRequest(
            hostname="SW1",
            device_type="switch",
            vlans=[VLANConfig(vlan_id=10, name="Sales")],
            interfaces=[
                InterfaceConfig(name="FastEthernet0/1", mode="access", access_vlan=50)
            ],
        )


def test_undeclared_trunk_allowed_vlan_raises_validation_error():
    """Trunk port allowing VLANs not declared on the switch must be rejected."""
    with pytest.raises(ValidationError, match="trunk allows VLANs \\[99\\] that are not declared"):
        ConfigGenerationRequest(
            hostname="SW1",
            device_type="switch",
            vlans=[VLANConfig(vlan_id=10, name="Sales")],
            interfaces=[
                InterfaceConfig(name="GigabitEthernet0/24", mode="trunk", allowed_vlans=[10, 99])
            ],
        )


def test_single_area_ospf_rejects_non_zero_area(generator):
    """Single-Area OSPF architecture must reject non-zero area network statements."""
    req = ConfigGenerationRequest(
        hostname="R1-SingleArea",
        routing_architecture="Single-Area OSPF (Area 0)",
        ospf=OSPFConfig(
            process_id=1,
            router_id="1.1.1.1",
            networks=[
                OSPFNetworkConfig(network="10.0.0.0", wildcard_mask="0.0.0.3", area=2)  # Non-zero!
            ],
        ),
    )
    with pytest.raises(ValueError, match="Single-Area OSPF architecture mandates Area 0"):
        generator.generate_config(req)


def test_missing_bgp_neighbor_details_rejected():
    """BGP configuration without any neighbors must be rejected."""
    with pytest.raises(ValidationError, match="must include at least one configured neighbor"):
        BGPConfig(local_as=65001, neighbors=[])


def test_bgp_same_as_rejected_as_invalid_ebgp():
    """Neighbor remote_as equal to local_as is iBGP, not eBGP; must be rejected."""
    with pytest.raises(ValidationError, match="eBGP requires distinct Autonomous System Numbers"):
        BGPConfig(
            local_as=65001,
            neighbors=[BGPNeighborConfig(ip_address="10.0.0.2", remote_as=65001)],
        )


def test_credential_exclusion_in_request():
    """Passing passwords or secrets in optional_settings must be strictly rejected."""
    with pytest.raises(ValidationError, match="Plaintext credential or secret keyword"):
        ConfigGenerationRequest(
            hostname="R1-Secure",
            optional_settings={"enable_password": "cisco123Secret"},
        )


def test_safe_export_filenames(generator):
    """Export filename must sanitize invalid characters and prevent traversal."""
    req = ConfigGenerationRequest(
        hostname="Edge-Router-01",
        device_type="router",
    )
    res = generator.generate_config(req)

    filename = res["export_filename"]
    assert filename.startswith("Edge-Router-01_")
    assert filename.endswith(".cfg")
    assert ".." not in filename
    assert "/" not in filename
    assert "\\" not in filename


# ==============================================================================
# 6. Explainability Audit Logging Tests
# ==============================================================================

def test_config_explainability_record_creation(generator):
    """Explainability record is logged with device parameters and IEEE/RFC standards."""
    req = ConfigGenerationRequest(
        network_name="Audit-Exam-Net",
        hostname="R-Audit-01",
        device_type="router",
        interfaces=[
            InterfaceConfig(name="GigabitEthernet0/0/0", ip_address="10.0.0.1", subnet_mask="255.255.255.0")
        ],
    )
    res = generator.generate_config(req)

    record_id = res["explainability_record_id"]
    assert record_id is not None

    record = generator.explainability_engine.get_explanation(record_id)
    assert record is not None
    assert record.engine_name == "ConfigGenerator"
    assert record.input_conditions["hostname"] == "R-Audit-01"
    assert "IEEE 802.1Q" in record.standards_and_rfcs[1]


# ==============================================================================
# 7. API Route Endpoint Integration Tests
# ==============================================================================

def test_api_route_info_endpoint():
    """GET / endpoint returns operational status and supported device targets."""
    info = configs_info()
    assert info["status"] == "ready"
    assert "Cisco IOS" in info["supported_targets"]


def test_api_route_successful_generate():
    """POST /generate endpoint generates valid configuration and registers it."""
    req = ConfigGenerationRequest(
        network_name="API-Test-Domain",
        hostname="SW-API-01",
        device_type="switch",
        vlans=[VLANConfig(vlan_id=10, name="Eng_Dept")],
    )
    res = generate_config(req)

    assert res["hostname"] == "SW-API-01"
    assert "vlan 10" in res["complete_config_text"]
    assert res["download_url"].startswith("/api/v1/configs/")

    # Fetch via GET /{config_id}
    config_id = res["config_id"]
    fetched = get_config_by_id(config_id)
    assert fetched["config_id"] == config_id
    assert fetched["hostname"] == "SW-API-01"


def test_api_route_download_endpoint():
    """GET /{config_id}/download securely returns a FileResponse."""
    req = ConfigGenerationRequest(
        network_name="Download-Domain",
        hostname="R-Download-01",
        device_type="router",
    )
    res = generate_config(req)
    config_id = res["config_id"]

    download_resp = download_config_file(config_id)
    assert isinstance(download_resp, FileResponse)
    assert str(download_resp.path).endswith(".cfg")


def test_api_route_nonexistent_config_raises_http_404():
    """GET on non-existent config_id must return HTTP 404."""
    with pytest.raises(HTTPException) as exc_info:
        get_config_by_id("non-existent-uuid-12345")
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        download_config_file("non-existent-uuid-12345")
    assert exc_info.value.status_code == 404
