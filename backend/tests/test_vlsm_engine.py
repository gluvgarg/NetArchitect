"""Comprehensive unit tests for the VLSM (Variable Length Subnet Masking) Engine.

Covers:
- Basic VLSM allocation with multiple subnets
- Descending host count sorting (RFC 1878)
- Subnet boundaries, broadcast, and network address calculations
- First and last usable IP address determination
- Default gateway convention (first usable IP)
- Non-overlapping subnet verification
- Subnet address alignment (boundary multiple of block size)
- Remaining unallocated address space and contiguous CIDR blocks
- Address space exhaustion (InsufficientAddressSpaceError)
- Invalid CIDR input validation (format and host bits set)
- Zero and negative host count validation
- Duplicate subnet requirement name rejection
- Empty subnet requirement list rejection
- Explainability engine audit record logging
- FastAPI route integration and HTTP response status codes
"""

import ipaddress
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi import HTTPException

# Ensure backend directory is in sys.path
import sys
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engines.vlsm_engine import VLSMEngine, InsufficientAddressSpaceError
from engines.explainability_engine import ExplainabilityEngine
from models.subnet import SubnetRequirement, VLSMRequest, SubnetAllocation, VLSMResponse
from api.routes.subnetting import calculate_vlsm


@pytest.fixture
def engine():
    """Provides a fresh VLSMEngine instance with isolated ExplainabilityEngine."""
    exp_engine = ExplainabilityEngine()
    return VLSMEngine(explainability_engine=exp_engine)


# ==============================================================================
# 1. Basic VLSM Allocation Tests
# ==============================================================================

def test_basic_vlsm_allocation_class_c(engine):
    """Test standard VLSM allocation in a /24 network with 3 subnets."""
    base_net = "192.168.1.0/24"
    requirements = [
        {"name": "Engineering", "required_hosts": 50},  # needs /26 (62 usable)
        {"name": "Sales", "required_hosts": 25},        # needs /27 (30 usable)
        {"name": "Point_to_Point", "required_hosts": 2}, # needs /30 (2 usable)
    ]

    result = engine.calculate_vlsm(base_net, requirements)

    assert result["root_network"] == base_net
    assert result["total_root_addresses"] == 256
    assert result["total_requested_hosts"] == 77
    assert len(result["subnets"]) == 3

    # Check Engineering (/26: 192.168.1.0 - 192.168.1.63)
    eng = result["subnets"][0]
    assert eng["name"] == "Engineering"
    assert eng["prefix_length"] == 26
    assert eng["network_address"] == "192.168.1.0"
    assert eng["subnet_mask"] == "255.255.255.192"
    assert eng["cidr_notation"] == "192.168.1.0/26"
    assert eng["first_usable_ip"] == "192.168.1.1"
    assert eng["default_gateway"] == "192.168.1.1"
    assert eng["last_usable_ip"] == "192.168.1.62"
    assert eng["broadcast_address"] == "192.168.1.63"
    assert eng["allocated_usable_hosts"] == 62
    assert eng["total_addresses"] == 64

    # Check Sales (/27: 192.168.1.64 - 192.168.1.95)
    sales = result["subnets"][1]
    assert sales["name"] == "Sales"
    assert sales["prefix_length"] == 27
    assert sales["network_address"] == "192.168.1.64"
    assert sales["subnet_mask"] == "255.255.255.224"
    assert sales["cidr_notation"] == "192.168.1.64/27"
    assert sales["first_usable_ip"] == "192.168.1.65"
    assert sales["default_gateway"] == "192.168.1.65"
    assert sales["last_usable_ip"] == "192.168.1.94"
    assert sales["broadcast_address"] == "192.168.1.95"
    assert sales["allocated_usable_hosts"] == 30
    assert sales["total_addresses"] == 32

    # Check Point_to_Point (/30: 192.168.1.96 - 192.168.1.99)
    p2p = result["subnets"][2]
    assert p2p["name"] == "Point_to_Point"
    assert p2p["prefix_length"] == 30
    assert p2p["network_address"] == "192.168.1.96"
    assert p2p["subnet_mask"] == "255.255.255.252"
    assert p2p["cidr_notation"] == "192.168.1.96/30"
    assert p2p["first_usable_ip"] == "192.168.1.97"
    assert p2p["last_usable_ip"] == "192.168.1.98"
    assert p2p["broadcast_address"] == "192.168.1.99"
    assert p2p["allocated_usable_hosts"] == 2
    assert p2p["total_addresses"] == 4

    # Check remaining address space (256 - 64 - 32 - 4 = 156)
    assert result["total_allocated_addresses"] == 100
    assert result["remaining_addresses"] == 156
    assert len(result["remaining_subnets"]) > 0
    assert result["address_utilization_percent"] == round((100 / 256) * 100, 2)
    assert "default gateway" in result["gateway_convention"].lower()


# ==============================================================================
# 2. Descending Sort Order Tests
# ==============================================================================

def test_descending_sort_order_enforced(engine):
    """Subnets supplied in arbitrary order must be sorted descending by host count."""
    base_net = "10.0.0.0/16"
    # Supplied in ascending order: 5 hosts, 20 hosts, 500 hosts, 1000 hosts
    requirements = [
        {"name": "Branch_Small", "required_hosts": 5},
        {"name": "Branch_Medium", "required_hosts": 20},
        {"name": "Campus_Users", "required_hosts": 500},
        {"name": "Datacenter", "required_hosts": 1000},
    ]

    result = engine.calculate_vlsm(base_net, requirements)

    # First allocated must be Datacenter (1000 hosts -> /22, 1024 IPs)
    assert result["subnets"][0]["name"] == "Datacenter"
    assert result["subnets"][0]["prefix_length"] == 22
    assert result["subnets"][0]["network_address"] == "10.0.0.0"

    # Second allocated must be Campus_Users (500 hosts -> /23, 512 IPs)
    assert result["subnets"][1]["name"] == "Campus_Users"
    assert result["subnets"][1]["prefix_length"] == 23
    assert result["subnets"][1]["network_address"] == "10.0.4.0"

    # Third allocated must be Branch_Medium (20 hosts -> /27, 32 IPs)
    assert result["subnets"][2]["name"] == "Branch_Medium"
    assert result["subnets"][2]["prefix_length"] == 27
    assert result["subnets"][2]["network_address"] == "10.0.6.0"

    # Fourth allocated must be Branch_Small (5 hosts -> /29, 8 IPs)
    assert result["subnets"][3]["name"] == "Branch_Small"
    assert result["subnets"][3]["prefix_length"] == 29
    assert result["subnets"][3]["network_address"] == "10.0.6.32"


# ==============================================================================
# 3. Non-Overlapping & Alignment Verification Tests
# ==============================================================================

def test_no_overlapping_subnets(engine):
    """Verify that none of the allocated subnets overlap each other."""
    base_net = "172.16.0.0/20"
    requirements = [
        {"name": "VLAN_10", "required_hosts": 400},
        {"name": "VLAN_20", "required_hosts": 200},
        {"name": "VLAN_30", "required_hosts": 100},
        {"name": "VLAN_40", "required_hosts": 50},
        {"name": "VLAN_50", "required_hosts": 14},
        {"name": "Link_1", "required_hosts": 2},
        {"name": "Link_2", "required_hosts": 2},
    ]

    result = engine.calculate_vlsm(base_net, requirements)
    root_network = ipaddress.IPv4Network(base_net)
    allocated_networks = [ipaddress.IPv4Network(s["cidr_notation"]) for s in result["subnets"]]

    # Verify every subnet is inside the root network
    for net in allocated_networks:
        assert net.subnet_of(root_network)

    # Verify no two subnets overlap
    for i in range(len(allocated_networks)):
        for j in range(i + 1, len(allocated_networks)):
            assert not allocated_networks[i].overlaps(allocated_networks[j]), (
                f"Subnets {allocated_networks[i]} and {allocated_networks[j]} overlap!"
            )


def test_subnet_address_boundary_alignment(engine):
    """Verify each allocated network address is aligned to an integer multiple of its block size."""
    base_net = "192.168.0.0/23"  # 512 addresses
    requirements = [
        {"name": "Dev", "required_hosts": 100},   # block 128
        {"name": "QA", "required_hosts": 50},     # block 64
        {"name": "Ops", "required_hosts": 12},    # block 16
        {"name": "Mgmt", "required_hosts": 2},    # block 4
    ]

    result = engine.calculate_vlsm(base_net, requirements)

    for subnet in result["subnets"]:
        net_int = int(ipaddress.IPv4Address(subnet["network_address"]))
        block_size = subnet["total_addresses"]
        assert net_int % block_size == 0, (
            f"Subnet {subnet['cidr_notation']} address is not aligned to its block size {block_size}"
        )


# ==============================================================================
# 4. Remaining Space & Utilization Calculations
# ==============================================================================

def test_full_utilization_no_remaining_space(engine):
    """When subnets perfectly consume the root network, remaining space is 0 and subnets list is empty."""
    base_net = "192.168.1.0/26"  # 64 addresses
    requirements = [
        {"name": "Sub_A", "required_hosts": 30},  # needs /27 (32 IPs)
        {"name": "Sub_B", "required_hosts": 30},  # needs /27 (32 IPs)
    ]

    result = engine.calculate_vlsm(base_net, requirements)

    assert result["total_allocated_addresses"] == 64
    assert result["remaining_addresses"] == 0
    assert result["remaining_subnets"] == []
    assert result["address_utilization_percent"] == 100.0


def test_remaining_contiguous_subnets_calculation(engine):
    """Verify that remaining unallocated space is correctly summarized into valid CIDR blocks."""
    base_net = "192.168.1.0/24"  # 256 addresses
    requirements = [
        {"name": "Half_Net", "required_hosts": 100},  # /25 (128 addresses)
    ]

    result = engine.calculate_vlsm(base_net, requirements)

    assert result["total_allocated_addresses"] == 128
    assert result["remaining_addresses"] == 128
    # Remaining 128 addresses must be represented by '192.168.1.128/25'
    assert result["remaining_subnets"] == ["192.168.1.128/25"]


# ==============================================================================
# 5. Error Handling & Validation Tests
# ==============================================================================

def test_insufficient_address_space_raises_error(engine):
    """Requesting more addresses than the root network provides raises InsufficientAddressSpaceError."""
    base_net = "192.168.1.0/28"  # 16 addresses total
    requirements = [
        {"name": "Big_LAN", "required_hosts": 30},  # needs /27 (32 addresses > 16)
    ]

    with pytest.raises(InsufficientAddressSpaceError) as exc_info:
        engine.calculate_vlsm(base_net, requirements)

    err = exc_info.value
    assert err.root_network == base_net
    assert err.total_root_addresses == 16
    assert err.deficit > 0
    assert "overflows the root network boundary" in err.message


def test_cumulative_exhaustion_raises_insufficient_space(engine):
    """Multiple subnets that cumulatively exhaust the root block raise InsufficientAddressSpaceError."""
    base_net = "192.168.1.0/25"  # 128 addresses
    requirements = [
        {"name": "LAN_1", "required_hosts": 50},  # /26 (64 addresses)
        {"name": "LAN_2", "required_hosts": 50},  # /26 (64 addresses)
        {"name": "LAN_3", "required_hosts": 10},  # /28 (16 addresses -> overflow!)
    ]

    with pytest.raises(InsufficientAddressSpaceError) as exc_info:
        engine.calculate_vlsm(base_net, requirements)

    assert exc_info.value.total_root_addresses == 128
    assert exc_info.value.deficit > 0


def test_invalid_cidr_format_raises_value_error(engine):
    """Invalid CIDR strings must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid root IPv4 network CIDR"):
        engine.calculate_vlsm("invalid_ip_string", [{"name": "A", "required_hosts": 10}])

    with pytest.raises(ValueError, match="Invalid root IPv4 network CIDR"):
        engine.calculate_vlsm("192.168.1.0/33", [{"name": "A", "required_hosts": 10}])


def test_cidr_with_host_bits_set_raises_value_error(engine):
    """Root network with host bits set (e.g. 192.168.1.5/24) must raise ValueError."""
    with pytest.raises(ValueError, match="has host bits set"):
        engine.calculate_vlsm("192.168.1.5/24", [{"name": "A", "required_hosts": 10}])


def test_zero_hosts_raises_value_error(engine):
    """Subnet requiring 0 hosts must raise ValueError."""
    with pytest.raises(ValueError, match="positive integer greater than 0"):
        engine.calculate_vlsm("192.168.1.0/24", [{"name": "Zero_Hosts", "required_hosts": 0}])


def test_negative_hosts_raises_value_error(engine):
    """Subnet requiring negative hosts must raise ValueError."""
    with pytest.raises(ValueError, match="positive integer greater than 0"):
        engine.calculate_vlsm("192.168.1.0/24", [{"name": "Neg_Hosts", "required_hosts": -5}])


def test_duplicate_subnet_names_raises_value_error(engine):
    """Duplicate subnet names (case-insensitive) must raise ValueError."""
    requirements = [
        {"name": "Servers", "required_hosts": 20},
        {"name": "servers", "required_hosts": 10},
    ]
    with pytest.raises(ValueError, match="Duplicate subnet requirement name detected"):
        engine.calculate_vlsm("192.168.1.0/24", requirements)


def test_empty_subnet_list_raises_value_error(engine):
    """Empty list of subnet requirements must raise ValueError."""
    with pytest.raises(ValueError, match="At least one subnet requirement"):
        engine.calculate_vlsm("192.168.1.0/24", [])


# ==============================================================================
# 6. Pydantic Model Validation Tests
# ==============================================================================

def test_pydantic_vlsm_request_valid():
    """Valid VLSMRequest model instantiation."""
    req = VLSMRequest(
        base_network="10.0.0.0/24",
        subnets=[
            SubnetRequirement(name="Office", required_hosts=50),
            SubnetRequirement(name="Lab", required_hosts=25),
        ],
    )
    assert req.base_network == "10.0.0.0/24"
    assert len(req.subnets) == 2


def test_pydantic_vlsm_request_rejects_duplicate_names():
    """Pydantic model rejects duplicate subnet names."""
    with pytest.raises(ValidationError):
        VLSMRequest(
            base_network="10.0.0.0/24",
            subnets=[
                SubnetRequirement(name="LAN_A", required_hosts=10),
                SubnetRequirement(name="lan_a", required_hosts=20),
            ],
        )


def test_pydantic_subnet_requirement_rejects_zero_or_negative():
    """Pydantic model rejects zero or negative required hosts."""
    with pytest.raises(ValidationError):
        SubnetRequirement(name="Valid", required_hosts=0)

    with pytest.raises(ValidationError):
        SubnetRequirement(name="Valid", required_hosts=-15)


def test_pydantic_subnet_requirement_rejects_empty_name():
    """Pydantic model rejects empty or whitespace-only names."""
    with pytest.raises(ValidationError):
        SubnetRequirement(name="   ", required_hosts=10)


# ==============================================================================
# 7. Explainability Engine Integration Tests
# ==============================================================================

def test_vlsm_explainability_audit_logging(engine):
    """Verify that calculate_vlsm logs decision trail to ExplainabilityEngine."""
    requirements = [
        {"name": "Staff", "required_hosts": 60},
        {"name": "Students", "required_hosts": 120},
    ]

    result = engine.calculate_vlsm("192.168.10.0/24", requirements)
    record_id = result["explainability_record_id"]
    assert record_id is not None

    record = engine.explainability_engine.get_explanation(record_id)
    assert record is not None
    assert record.engine_name == "VLSMEngine"
    assert "RFC 4632" in record.standards_and_rfcs[0]
    assert "RFC 1878" in record.standards_and_rfcs[1]
    assert "Students" in record.input_conditions["sorting_order"][0]
    assert "Staff" in record.input_conditions["sorting_order"][1]


# ==============================================================================
# 8. API Route Endpoint Integration Tests
# ==============================================================================

def test_api_route_successful_vlsm_calculation():
    """POST /calculate endpoint returns 200 OK and valid VLSMResponse schema."""
    req = VLSMRequest(
        base_network="192.168.1.0/24",
        subnets=[
            SubnetRequirement(name="HR", required_hosts=50),
            SubnetRequirement(name="Finance", required_hosts=20),
        ],
    )
    response = calculate_vlsm(req)

    assert response["root_network"] == "192.168.1.0/24"
    assert len(response["subnets"]) == 2
    assert response["subnets"][0]["name"] == "HR"
    assert response["subnets"][0]["default_gateway"] == "192.168.1.1"
    assert response["subnets"][1]["name"] == "Finance"
    assert response["subnets"][1]["default_gateway"] == "192.168.1.65"


def test_api_route_insufficient_space_raises_http_400():
    """POST /calculate endpoint raises HTTP 400 for exhausted address space."""
    req = VLSMRequest(
        base_network="192.168.1.0/28",  # 16 IPs
        subnets=[
            SubnetRequirement(name="Overloaded", required_hosts=50),  # needs 64 IPs
        ],
    )
    with pytest.raises(HTTPException) as exc_info:
        calculate_vlsm(req)

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert detail["error_type"] == "InsufficientAddressSpaceError"
    assert detail["root_network"] == "192.168.1.0/28"
    assert detail["total_root_addresses"] == 16
    assert detail["deficit"] > 0
