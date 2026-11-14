"""Pydantic models for VLSM (Variable Length Subnet Masking) calculations."""

import ipaddress
from typing import List, Optional, Set
from pydantic import BaseModel, Field, field_validator, model_validator


class SubnetRequirement(BaseModel):
    """Host requirement for an individual subnet."""
    name: str = Field(..., min_length=1, description="Unique label for the subnet (e.g. 'Engineering_LAN')")
    required_hosts: int = Field(..., gt=0, description="Usable host IP addresses needed (must be positive integer >= 1)")

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        """Ensure subnet name is not empty or just whitespace."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Subnet name cannot be empty or whitespace only.")
        return cleaned

    @field_validator("required_hosts")
    @classmethod
    def validate_positive_hosts(cls, v: int) -> int:
        """Reject zero or negative host requirements."""
        if v is None or v <= 0:
            raise ValueError(f"Required hosts must be a positive integer greater than 0. Received: {v}")
        return v


class VLSMRequest(BaseModel):
    """Input payload for VLSM computation."""
    base_network: str = Field(..., description="Root IPv4 network in CIDR notation (e.g. '192.168.1.0/24')")
    subnets: List[SubnetRequirement] = Field(..., min_length=1, description="List of required subnets with host counts")

    @field_validator("base_network")
    @classmethod
    def validate_ipv4_cidr(cls, v: str) -> str:
        """Ensure base_network is a valid IPv4 CIDR block with host bits unset."""
        if not v or not isinstance(v, str):
            raise ValueError("base_network must be a non-empty string.")
        cleaned = v.strip()
        try:
            net = ipaddress.IPv4Network(cleaned, strict=True)
        except ValueError as err:
            raise ValueError(
                f"Invalid root IPv4 network CIDR '{cleaned}': {str(err)}. "
                f"Ensure valid CIDR notation with host bits unset (e.g. '192.168.1.0/24')."
            )
        return str(net)

    @field_validator("subnets")
    @classmethod
    def validate_unique_subnet_names(cls, v: List[SubnetRequirement]) -> List[SubnetRequirement]:
        """Ensure subnet names within the request are unique."""
        if not v:
            raise ValueError("At least one subnet requirement must be specified.")
        seen: Set[str] = set()
        for item in v:
            name_key = item.name.strip().lower()
            if name_key in seen:
                raise ValueError(
                    f"Duplicate subnet requirement name detected: '{item.name}'. "
                    f"Subnet requirement names must be unique within a plan."
                )
            seen.add(name_key)
        return v


class SubnetAllocation(BaseModel):
    """Detailed allocation metrics for a single calculated subnet."""
    name: str = Field(..., description="Subnet label")
    required_hosts: int = Field(..., description="Number of usable hosts requested")
    allocated_usable_hosts: int = Field(..., description="Usable host addresses provided (2^(32-p) - 2)")
    allocated_hosts: int = Field(..., description="Backward-compatibility alias for allocated_usable_hosts")
    total_addresses: int = Field(..., description="Total addresses in the block including network and broadcast")
    network_address: str = Field(..., description="Subnet network address")
    prefix_length: int = Field(..., description="CIDR prefix length (e.g. 26)")
    subnet_mask: str = Field(..., description="Dotted decimal subnet mask (e.g. '255.255.255.192')")
    cidr_notation: str = Field(..., description="Full CIDR notation (e.g. '192.168.1.0/26')")
    first_usable_ip: str = Field(..., description="First usable host address (also default gateway)")
    last_usable_ip: str = Field(..., description="Last usable host address in range")
    broadcast_address: str = Field(..., description="Directed broadcast address")
    default_gateway: str = Field(..., description="Assigned default gateway (first usable IP)")
    usable_range: str = Field(..., description="Formatted usable IP address range")


class VLSMResponse(BaseModel):
    """Full hierarchical VLSM allocation plan and address space metrics."""
    root_network: str = Field(..., description="Original root CIDR block")
    subnets: List[SubnetAllocation] = Field(..., description="Calculated subnet allocations")
    total_requested_hosts: int = Field(..., description="Sum of all requested usable hosts")
    total_allocated_usable_hosts: int = Field(..., description="Sum of usable host capacities provided across all subnets")
    total_root_addresses: int = Field(..., description="Total address capacity of the root network")
    total_allocated_addresses: int = Field(..., description="Total addresses consumed including network/broadcast overhead")
    remaining_addresses: int = Field(..., description="Unallocated addresses remaining in root network")
    remaining_subnets: List[str] = Field(default_factory=list, description="Contiguous unallocated CIDR blocks available")
    address_utilization_percent: float = Field(..., description="Percentage of root addresses allocated")
    efficiency_ratio: float = Field(..., description="Ratio of requested hosts to allocated usable hosts")
    gateway_convention: str = Field(..., description="Default gateway assignment policy")
    explainability_record_id: Optional[str] = Field(None, description="Audit record ID in ExplainabilityEngine")
    standards_and_rfcs: List[str] = Field(default_factory=list, description="Governing RFC and standard citations")
    rationale: str = Field(..., description="Technical reasoning detailing sorting, prefix selection, and alignment")
