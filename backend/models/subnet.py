"""Pydantic models for VLSM Subnetting calculations."""

from typing import List, Optional
from pydantic import BaseModel, Field


class SubnetRequirement(BaseModel):
    """Host requirements for an individual subnet."""
    name: str = Field(..., description="Subnet label (e.g. 'Engineering_LAN')")
    required_hosts: int = Field(..., gt=0, description="Number of usable host addresses needed")


class VLSMRequest(BaseModel):
    """Input payload for VLSM computation."""
    base_network: str = Field(..., description="Root network in CIDR notation (e.g. '192.168.10.0/24')")
    subnets: List[SubnetRequirement] = Field(..., min_length=1, description="List of required subnets")


class SubnetAllocation(BaseModel):
    """Detailed allocation metrics for a single calculated subnet."""
    name: str
    required_hosts: int
    allocated_hosts: int
    network_address: str
    prefix_length: int
    subnet_mask: str
    first_usable_ip: str
    last_usable_ip: str
    broadcast_address: str
