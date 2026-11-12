"""Academic helper utilities for IP and CIDR calculations."""

import ipaddress
from typing import Optional


def is_valid_ipv4(address_str: str) -> bool:
    """Check if the string is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(address_str.strip())
        return True
    except (ValueError, AttributeError):
        return False


def cidr_to_netmask(prefix_length: int) -> Optional[str]:
    """Convert CIDR prefix (e.g. 24) to dotted decimal netmask (e.g. '255.255.255.0')."""
    if not 0 <= prefix_length <= 32:
        return None
    mask_int = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF
    return str(ipaddress.IPv4Address(mask_int))


def netmask_to_cidr(netmask_str: str) -> Optional[int]:
    """Convert dotted-decimal netmask to CIDR prefix integer."""
    try:
        network = ipaddress.IPv4Network(f"0.0.0.0/{netmask_str.strip()}")
        return network.prefixlen
    except (ValueError, AttributeError):
        return None
