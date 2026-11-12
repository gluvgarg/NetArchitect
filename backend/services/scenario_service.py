"""Scenario Service managing the standard network profiles.

Profiles managed:
1. Campus LAN (Local Area Network)
2. Metro MAN (Metropolitan Area Network)
3. Global WAN (Wide Area Network)
"""

from typing import Dict, Any, List, Optional


class ScenarioService:
    """Service responsible for loading, serving, and validating network scenario profiles."""

    def __init__(self):
        self._profiles: Dict[str, Dict[str, Any]] = {
            "campus_lan": {
                "id": "campus_lan",
                "name": "Campus LAN",
                "full_name": "Campus Local Area Network",
                "scope": "Local / Enterprise Campus",
                "max_diameter_meters": 2000,
                "bandwidth_target": "1 Gbps - 10 Gbps",
                "typical_latency_ms": "< 5 ms",
                "physical_media": [
                    "Copper Cat6/Cat6a for horizontal drops (< 100m)",
                    "Multi-mode Fiber (OM3/OM4) or Single-mode (OS2) for inter-building backbone"
                ],
                "recommended_routing": "OSPF (Area 0 Backbone)",
                "layer_2_features": ["IEEE 802.1Q VLANs", "RSTP/MSTP", "LACP Link Aggregation"],
                "addressing_strategy": "RFC 1918 Private IPv4 (e.g. 10.0.0.0/8 or 172.16.0.0/12) with VLSM",
                "description": "High-throughput, low-latency network spanning university or enterprise buildings."
            },
            "metro_man": {
                "id": "metro_man",
                "name": "Metro MAN",
                "full_name": "Metropolitan Area Network",
                "scope": "City / Municipal Interconnect",
                "max_diameter_meters": 50000,
                "bandwidth_target": "1 Gbps - 40 Gbps",
                "typical_latency_ms": "5 - 20 ms",
                "physical_media": [
                    "Single-mode Optical Fiber (OS2 with 10GBASE-LR / 10GBASE-ER)",
                    "Carrier Ethernet or Dark Fiber links"
                ],
                "recommended_routing": "Multi-area OSPF or IS-IS",
                "layer_2_features": ["Carrier Ethernet (E-Line/E-LAN)", "802.1ad QinQ", "MPLS"],
                "addressing_strategy": "Aggregated CIDR blocks with hierarchical regional distribution",
                "description": "Interconnects geographically separated branch offices, municipal centers, or campuses across a city."
            },
            "global_wan": {
                "id": "global_wan",
                "name": "Global WAN",
                "full_name": "Global Wide Area Network",
                "scope": "Inter-regional / Transcontinental",
                "max_diameter_meters": 40000000,
                "bandwidth_target": "100 Mbps - 10 Gbps",
                "typical_latency_ms": "30 - 150+ ms",
                "physical_media": [
                    "Submarine Cable Systems",
                    "Leased Long-haul DWDM Fiber Circuits",
                    "Satellite / Point-to-Point Terrestrial Microwave"
                ],
                "recommended_routing": "BGP-4 (Border Gateway Protocol - RFC 4271)",
                "layer_2_features": ["SD-WAN Overlays", "IPSec Cryptographic Tunnels", "MPLS Layer 3 VPN"],
                "addressing_strategy": "Public Autonomous System (AS) Numbers with Public / NAT-ed addressing",
                "description": "Connects international branch sites and data centers across public carriers and Autonomous Systems."
            }
        }

    def list_profiles(self) -> List[Dict[str, Any]]:
        """Return list of all supported network profile summaries."""
        return list(self._profiles.values())

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific profile by its identifier."""
        return self._profiles.get(profile_id.lower())

    def validate_profile_suitability(
        self,
        distance_meters: float,
        location_count: int
    ) -> str:
        """Determines the appropriate profile classification based on geographic distance."""
        if distance_meters <= 2000:
            return "campus_lan"
        elif distance_meters <= 50000:
            return "metro_man"
        else:
            return "global_wan"


# Singleton instance
scenario_service = ScenarioService()
