"""VLSM & Subnetting Engine.

Academic Context:
Performs Variable Length Subnet Masking (VLSM) and CIDR address space decomposition
to maximize IPv4 address conservation and prevent address fragmentation in hierarchical networks.

Standards & References:
- RFC 1878: Variable Length Subnet Table For IPv4
- RFC 4632: Classless Inter-domain Routing (CIDR): The Internet Address Assignment and Aggregation Plan
- RFC 1918: Address Allocation for Private Internets
"""

import math
import ipaddress
from typing import List, Dict, Any, Optional, Set, Union
from engines.explainability_engine import ExplainabilityEngine


class InsufficientAddressSpaceError(ValueError):
    """Raised when the root network block cannot accommodate the requested subnet requirements."""

    def __init__(
        self,
        message: str,
        root_network: str = "",
        total_root_addresses: int = 0,
        total_required_addresses: int = 0,
        deficit: int = 0,
    ):
        super().__init__(message)
        self.message = message
        self.root_network = root_network
        self.total_root_addresses = total_root_addresses
        self.total_required_addresses = total_required_addresses
        self.deficit = deficit


class VLSMEngine:
    """Engine responsible for hierarchical IP allocation using Variable Length Subnet Masking (VLSM)."""

    GATEWAY_CONVENTION: str = "First usable IP address is assigned as the default gateway."

    def __init__(self, explainability_engine: Optional[ExplainabilityEngine] = None):
        self.explainability_engine = explainability_engine or ExplainabilityEngine()
        self.is_ready = True

    @staticmethod
    def calculate_prefix_for_hosts(required_hosts: int) -> int:
        """Calculates the smallest suitable IPv4 subnet prefix length for a given usable host count.

        Formula:
            Find smallest integer h (host bits >= 2) such that 2^h - 2 >= required_hosts.
            Prefix length p = 32 - h.

        Args:
            required_hosts: Required usable host count (must be >= 1).

        Returns:
            CIDR prefix length integer (e.g. 25 for 100 hosts).

        Raises:
            ValueError: If required_hosts < 1 or exceeds IPv4 address capacity.
        """
        if required_hosts is None or required_hosts < 1:
            raise ValueError(
                f"Required hosts must be a positive integer greater than 0. Received: {required_hosts}"
            )

        # Conventional IPv4 subnets reserve 1 network address and 1 broadcast address
        total_needed = required_hosts + 2

        # Smallest power of 2 >= total_needed
        host_bits = math.ceil(math.log2(total_needed))

        # Conventional host subnets require at least /30 (2 host bits, 2 usable hosts)
        if host_bits < 2:
            host_bits = 2

        prefix = 32 - host_bits
        if prefix < 0:
            raise ValueError(
                f"Requested host count ({required_hosts}) exceeds 32-bit IPv4 address space capacity."
            )

        return prefix

    def calculate_vlsm(
        self,
        base_network: str,
        subnets_needed: List[Union[Dict[str, Any], Any]]
    ) -> Dict[str, Any]:
        """Calculates an optimized VLSM subnet allocation plan for a root IPv4 network.

        Steps:
        1. Parse and validate root network in CIDR notation (enforcing strict network boundary).
        2. Validate subnet requirements (non-empty, positive hosts, unique names).
        3. Sort requirements in descending order of required host count to prevent fragmentation.
        4. Sequentially allocate blocks with mathematical address-alignment enforcement (N % B == 0).
        5. Verify that allocations do not exceed root network boundaries.
        6. Compute unallocated contiguous address blocks and utilization metrics.
        7. Audit log the decision trail via the ExplainabilityEngine.

        Args:
            base_network: Root network block in CIDR notation (e.g. '192.168.1.0/24').
            subnets_needed: List of required subnets with names and host counts.

        Returns:
            Dict containing full VLSM plan, allocated subnets, remaining blocks, and metrics.

        Raises:
            ValueError: On invalid CIDR, zero/negative host requirements, or duplicate names.
            InsufficientAddressSpaceError: If root network address space is exhausted.
        """
        # 1. Parse and Validate Root Network
        if not base_network or not isinstance(base_network, str):
            raise ValueError("Root network 'base_network' must be a non-empty string.")

        try:
            root_net = ipaddress.IPv4Network(base_network.strip(), strict=True)
        except ValueError as err:
            raise ValueError(
                f"Invalid root IPv4 network CIDR '{base_network}': {str(err)}. "
                f"Ensure valid CIDR notation with host bits unset (e.g. '192.168.1.0/24')."
            )

        # 2. Validate Subnet Requirements
        if not subnets_needed:
            raise ValueError("At least one subnet requirement must be specified.")

        seen_names: Set[str] = set()
        normalized_requirements: List[Dict[str, Any]] = []

        for item in subnets_needed:
            if isinstance(item, dict):
                name = item.get("name")
                req_hosts = item.get("required_hosts")
            else:
                name = getattr(item, "name", None)
                req_hosts = getattr(item, "required_hosts", None)

            if not name or not str(name).strip():
                raise ValueError("Subnet requirement name cannot be empty or whitespace only.")

            cleaned_name = str(name).strip()
            name_key = cleaned_name.lower()
            if name_key in seen_names:
                raise ValueError(
                    f"Duplicate subnet requirement name detected: '{cleaned_name}'. "
                    f"Subnet requirement names must be unique within a plan."
                )
            seen_names.add(name_key)

            if req_hosts is None or not isinstance(req_hosts, int) or req_hosts <= 0:
                raise ValueError(
                    f"Subnet '{cleaned_name}' required hosts must be a positive integer greater than 0. Received: {req_hosts}"
                )

            normalized_requirements.append({
                "name": cleaned_name,
                "required_hosts": req_hosts,
            })

        # 3. Sort Subnet Requirements by Descending Host Count (Core VLSM Principle)
        sorted_subnets = sorted(
            normalized_requirements,
            key=lambda x: x["required_hosts"],
            reverse=True,
        )

        # 4. Sequential Allocation with Boundary Alignment
        current_ip_int = int(root_net.network_address)
        root_end_ip_int = int(root_net.broadcast_address)
        allocations: List[Dict[str, Any]] = []
        prefix_calculations: List[Dict[str, Any]] = []
        total_allocated_addresses = 0

        for req in sorted_subnets:
            name = req["name"]
            req_hosts = req["required_hosts"]

            prefix = self.calculate_prefix_for_hosts(req_hosts)
            block_size = 2 ** (32 - prefix)
            usable_hosts = block_size - 2

            # Mathematical alignment: address must be a multiple of block_size
            if current_ip_int % block_size != 0:
                current_ip_int = ((current_ip_int + block_size - 1) // block_size) * block_size

            subnet_end_ip_int = current_ip_int + block_size - 1

            # Check if block overflows root network boundary
            if subnet_end_ip_int > root_end_ip_int:
                deficit = subnet_end_ip_int - root_end_ip_int
                raise InsufficientAddressSpaceError(
                    message=(
                        f"Insufficient address space in root network '{root_net}'. "
                        f"Subnet '{name}' requires prefix /{prefix} ({block_size} addresses for {req_hosts} hosts), "
                        f"which overflows the root network boundary by {deficit} addresses."
                    ),
                    root_network=str(root_net),
                    total_root_addresses=root_net.num_addresses,
                    total_required_addresses=total_allocated_addresses + block_size,
                    deficit=deficit,
                )

            # Instantiate IPv4Network for allocated block
            subnet_obj = ipaddress.IPv4Network((current_ip_int, prefix))
            first_usable = str(subnet_obj.network_address + 1)
            last_usable = str(subnet_obj.broadcast_address - 1)

            allocations.append({
                "name": name,
                "required_hosts": req_hosts,
                "allocated_usable_hosts": usable_hosts,
                "allocated_hosts": usable_hosts,  # Backward compatibility alias
                "total_addresses": block_size,
                "network_address": str(subnet_obj.network_address),
                "prefix_length": prefix,
                "subnet_mask": str(subnet_obj.netmask),
                "cidr_notation": str(subnet_obj),
                "first_usable_ip": first_usable,
                "last_usable_ip": last_usable,
                "broadcast_address": str(subnet_obj.broadcast_address),
                "default_gateway": first_usable,  # Documented gateway convention
                "usable_range": f"{first_usable} - {last_usable}",
            })

            prefix_calculations.append({
                "name": name,
                "required_hosts": req_hosts,
                "calculated_prefix": f"/{prefix}",
                "block_size": block_size,
                "usable_hosts": usable_hosts,
            })

            total_allocated_addresses += block_size
            current_ip_int = subnet_end_ip_int + 1

        # 5. Remaining Address Space & Metrics
        remaining_addresses = root_net.num_addresses - total_allocated_addresses
        remaining_subnets: List[str] = []

        if current_ip_int <= root_end_ip_int:
            unallocated_ranges = ipaddress.summarize_address_range(
                ipaddress.IPv4Address(current_ip_int),
                root_net.broadcast_address,
            )
            remaining_subnets = [str(net) for net in unallocated_ranges]

        total_requested_hosts = sum(r["required_hosts"] for r in sorted_subnets)
        total_allocated_usable_hosts = sum(a["allocated_usable_hosts"] for a in allocations)
        utilization_percent = round((total_allocated_addresses / root_net.num_addresses) * 100, 2)
        efficiency_ratio = (
            round(total_requested_hosts / total_allocated_usable_hosts, 4)
            if total_allocated_usable_hosts > 0
            else 0.0
        )

        # 6. Technical Reasoning & Explainability Logging
        sort_order_summary = ", ".join(f"{r['name']} ({r['required_hosts']} hosts)" for r in sorted_subnets)
        alloc_summary = "; ".join(f"{a['name']}: {a['cidr_notation']} ({a['allocated_usable_hosts']} usable)" for a in allocations)

        technical_reasoning = (
            f"Variable Length Subnet Masking (VLSM) Allocation Plan for Root Network {root_net} ({root_net.num_addresses} total IPs):\n"
            f"1. Descending Sort Order (RFC 1878): Requirements were sorted in descending order of host count "
            f"[{sort_order_summary}] to prevent address fragmentation and satisfy binary boundary alignments.\n"
            f"2. Prefix Selection: Sized each subnet using 2^(32-p) - 2 >= H (e.g. {prefix_calculations[0]['name']} "
            f"needs {prefix_calculations[0]['required_hosts']} hosts -> {prefix_calculations[0]['calculated_prefix']}).\n"
            f"3. Alignment & Allocations: Sequential allocations strictly aligned to multiples of block size: [{alloc_summary}].\n"
            f"4. Address Space Utilization: Consumed {total_allocated_addresses}/{root_net.num_addresses} addresses ({utilization_percent}%). "
            f"Remaining unallocated capacity: {remaining_addresses} addresses across {len(remaining_subnets)} contiguous block(s): {remaining_subnets}.\n"
            f"5. Gateway Convention: {self.GATEWAY_CONVENTION}"
        )

        explanation_record = self.explainability_engine.record_explanation(
            engine_name="VLSMEngine",
            input_conditions={
                "root_network": str(root_net),
                "requested_subnets": [
                    {"name": r["name"], "required_hosts": r["required_hosts"]}
                    for r in normalized_requirements
                ],
                "sorting_order": [r["name"] for r in sorted_subnets],
            },
            selected_recommendation={
                "allocations": [
                    {
                        "name": a["name"],
                        "cidr": a["cidr_notation"],
                        "prefix": a["prefix_length"],
                        "usable_hosts": a["allocated_usable_hosts"],
                        "gateway": a["default_gateway"],
                    }
                    for a in allocations
                ],
                "total_allocated_addresses": total_allocated_addresses,
                "remaining_addresses": remaining_addresses,
                "remaining_subnets": remaining_subnets,
                "utilization_percent": utilization_percent,
            },
            technical_reasoning=technical_reasoning,
            standards_and_rfcs=[
                "RFC 4632: Classless Inter-domain Routing (CIDR): The Internet Address Assignment and Aggregation Plan",
                "RFC 1878: Variable Length Subnet Table For IPv4",
            ],
        )

        return {
            "root_network": str(root_net),
            "subnets": allocations,
            "total_requested_hosts": total_requested_hosts,
            "total_allocated_usable_hosts": total_allocated_usable_hosts,
            "total_root_addresses": root_net.num_addresses,
            "total_allocated_addresses": total_allocated_addresses,
            "remaining_addresses": remaining_addresses,
            "remaining_subnets": remaining_subnets,
            "address_utilization_percent": utilization_percent,
            "efficiency_ratio": efficiency_ratio,
            "gateway_convention": self.GATEWAY_CONVENTION,
            "explainability_record_id": explanation_record.record_id,
            "standards_and_rfcs": [
                "RFC 4632: Classless Inter-domain Routing (CIDR): The Internet Address Assignment and Aggregation Plan",
                "RFC 1878: Variable Length Subnet Table For IPv4",
            ],
            "rationale": technical_reasoning,
        }
