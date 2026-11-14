"""Pydantic models for Network Device Configuration Generation.

Academic Context:
Provides structured request and response models for Cisco IOS CLI configuration
generation, enforcing validation on Layer 2 VLAN tagging (IEEE 802.1Q),
Layer 3 IP addressing, OSPF process/area design (RFC 2328), and eBGP peering (RFC 4271).
Distinguishes input/topology constraint validation from device-level syntax verification.
"""

from typing import List, Optional, Dict, Any, Union
import re
import ipaddress
from pydantic import BaseModel, Field, field_validator, model_validator


class VLANConfig(BaseModel):
    """VLAN configuration definition (IEEE 802.1Q)."""

    vlan_id: int = Field(
        ...,
        ge=1,
        le=4094,
        description="Standard 802.1Q VLAN ID (1-4094)",
        examples=[10],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="VLAN administrative identifier name",
        examples=["Management_VLAN"],
    )
    description: Optional[str] = Field(None, description="Optional VLAN description")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("VLAN name cannot be empty or whitespace.")
        if not re.match(r"^[A-Za-z0-9_-]+$", clean):
            raise ValueError(f"VLAN name '{clean}' contains invalid characters. Use alphanumeric, underscore, or hyphen.")
        return clean


class InterfaceConfig(BaseModel):
    """Interface configuration parameter model."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Interface identifier (e.g., GigabitEthernet0/0/0, FastEthernet0/1, Vlan10)",
        examples=["GigabitEthernet0/0/0"],
    )
    description: Optional[str] = Field(None, description="Interface descriptive label")
    ip_address: Optional[str] = Field(None, description="IPv4 host address assigned to interface")
    subnet_mask: Optional[str] = Field(None, description="IPv4 dotted-decimal subnet mask (e.g. 255.255.255.0)")
    mode: Optional[str] = Field(
        None,
        description="Interface switchport operational mode: 'access', 'trunk', 'routed', or None",
    )
    access_vlan: Optional[int] = Field(
        None,
        ge=1,
        le=4094,
        description="VLAN ID assigned in access mode",
    )
    allowed_vlans: Optional[List[int]] = Field(
        None,
        description="Explicit list of allowed VLAN IDs for trunk mode",
    )
    enabled: bool = Field(True, description="True for 'no shutdown', False for 'shutdown'")
    ospf_area: Optional[Union[int, str]] = Field(None, description="Interface-level OSPF area assignment")
    media_type: Optional[str] = Field(None, description="Physical media reference (e.g., Cat6a, OM4, OS2)")

    # Backward compatibility aliases
    is_trunk: bool = Field(False, description="Legacy flag indicating trunk port mode")
    vlan_id: Optional[int] = Field(None, description="Legacy field for access vlan_id")

    @field_validator("name")
    @classmethod
    def validate_interface_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Interface name cannot be empty.")
        return clean

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None
        try:
            ip = ipaddress.IPv4Address(clean)
            if ip.is_multicast:
                raise ValueError(f"Multicast IP {clean} cannot be assigned to a device interface.")
            if ip.is_reserved:
                raise ValueError(f"Reserved IP {clean} cannot be assigned to a device interface.")
            return clean
        except ipaddress.AddressValueError as err:
            raise ValueError(f"Invalid interface IPv4 address '{clean}': {err}")

    @field_validator("subnet_mask")
    @classmethod
    def validate_mask(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None
        # Support dotted decimal e.g. 255.255.255.0 or prefix e.g. /24
        if clean.startswith("/"):
            try:
                prefix = int(clean[1:])
                if prefix < 0 or prefix > 32:
                    raise ValueError(f"Invalid prefix length '{clean}'.")
                net = ipaddress.IPv4Network(f"0.0.0.0/{prefix}")
                return str(net.netmask)
            except ValueError as err:
                raise ValueError(f"Invalid subnet mask prefix '{clean}': {err}")
        try:
            ipaddress.IPv4Network(f"0.0.0.0/{clean}")
            return clean
        except (ValueError, ipaddress.NetmaskValueError) as err:
            raise ValueError(f"Invalid dotted-decimal subnet mask '{clean}': {err}")

    @model_validator(mode="after")
    def reconcile_interface_modes_and_addressing(self) -> "InterfaceConfig":
        # Reconcile legacy fields
        if self.is_trunk and not self.mode:
            self.mode = "trunk"
        if self.vlan_id and not self.access_vlan:
            self.access_vlan = self.vlan_id
        if self.access_vlan and not self.mode:
            self.mode = "access"

        # Check IP/mask pairing
        if self.ip_address and not self.subnet_mask:
            raise ValueError(f"Interface '{self.name}' has an IP address ({self.ip_address}) but lacks a subnet mask.")
        if self.subnet_mask and not self.ip_address:
            raise ValueError(f"Interface '{self.name}' has a subnet mask ({self.subnet_mask}) but lacks an IP address.")

        # Check mode consistency
        if self.mode:
            normalized_mode = self.mode.strip().lower()
            if normalized_mode not in {"access", "trunk", "routed"}:
                raise ValueError(f"Interface mode must be 'access', 'trunk', or 'routed'; got '{self.mode}'.")
            self.mode = normalized_mode

            if self.mode == "access" and self.allowed_vlans:
                raise ValueError(f"Interface '{self.name}' is in access mode; allowed_vlans is only valid for trunk ports.")
            if self.mode == "trunk" and self.access_vlan:
                raise ValueError(f"Interface '{self.name}' is in trunk mode; access_vlan is only valid for access ports.")

        return self


class OSPFNetworkConfig(BaseModel):
    """OSPF network advertisement statement."""

    network: str = Field(..., description="Network address to advertise", examples=["10.0.0.0"])
    wildcard_mask: str = Field(..., description="OSPF wildcard mask (e.g. 0.0.0.3)", examples=["0.0.0.3"])
    area: Union[int, str] = Field(..., description="OSPF area identifier (e.g. 0 or 1)", examples=[0])

    @field_validator("network")
    @classmethod
    def validate_net(cls, v: str) -> str:
        try:
            ipaddress.IPv4Address(v.strip())
            return v.strip()
        except ValueError as err:
            raise ValueError(f"Invalid OSPF network address '{v}': {err}")

    @field_validator("wildcard_mask")
    @classmethod
    def validate_wildcard(cls, v: str) -> str:
        clean = v.strip()
        parts = clean.split(".")
        if len(parts) != 4:
            raise ValueError(f"Invalid wildcard mask '{clean}'. Must be 4 dotted octets.")
        for part in parts:
            try:
                octet = int(part)
                if octet < 0 or octet > 255:
                    raise ValueError(f"Octet {octet} out of range (0-255).")
            except ValueError:
                raise ValueError(f"Invalid octet '{part}' in wildcard mask '{clean}'.")
        return clean

    @field_validator("area")
    @classmethod
    def validate_area(cls, v: Union[int, str]) -> Union[int, str]:
        if isinstance(v, int):
            if v < 0 or v > 4294967295:
                raise ValueError(f"OSPF area ID {v} out of range (0-4294967295).")
            return v
        clean = v.strip()
        if clean.isdigit():
            val = int(clean)
            if val < 0 or val > 4294967295:
                raise ValueError(f"OSPF area ID {clean} out of range.")
            return val
        try:
            ipaddress.IPv4Address(clean)
            return clean
        except ValueError:
            raise ValueError(f"OSPF area '{clean}' must be an integer (0-4294967295) or dotted decimal (e.g. 0.0.0.0).")


class OSPFConfig(BaseModel):
    """OSPF process configuration parameters (RFC 2328)."""

    process_id: int = Field(1, ge=1, le=65535, description="OSPF process identifier (1-65535)")
    router_id: str = Field(..., description="OSPF 32-bit Router ID in dotted decimal notation", examples=["1.1.1.1"])
    networks: List[OSPFNetworkConfig] = Field(default_factory=list, description="Explicit network statements")
    passive_interfaces: List[str] = Field(default_factory=list, description="Interfaces designated as passive")

    @field_validator("router_id")
    @classmethod
    def validate_router_id(cls, v: str) -> str:
        clean = v.strip()
        try:
            ip = ipaddress.IPv4Address(clean)
            if ip.is_multicast or ip.is_loopback:
                raise ValueError(f"Router ID cannot be loopback or multicast address: '{clean}'.")
            return clean
        except ipaddress.AddressValueError as err:
            raise ValueError(f"Invalid OSPF router ID '{clean}': {err}")


class BGPNeighborConfig(BaseModel):
    """eBGP peer neighbor configuration parameters (RFC 4271)."""

    ip_address: str = Field(..., description="Neighbor IPv4 address", examples=["198.51.100.1"])
    remote_as: int = Field(..., ge=1, le=4294967295, description="Neighbor Autonomous System Number", examples=[65000])
    description: Optional[str] = Field(None, description="Neighbor administrative description")

    @field_validator("ip_address")
    @classmethod
    def validate_neighbor_ip(cls, v: str) -> str:
        clean = v.strip()
        try:
            ipaddress.IPv4Address(clean)
            return clean
        except ipaddress.AddressValueError as err:
            raise ValueError(f"Invalid BGP neighbor IP address '{clean}': {err}")


class BGPNetworkConfig(BaseModel):
    """BGP network prefix advertisement."""

    network: str = Field(..., description="Network prefix address", examples=["10.0.0.0"])
    mask: str = Field(..., description="Subnet mask in dotted decimal", examples=["255.255.0.0"])

    @field_validator("network")
    @classmethod
    def validate_bgp_net(cls, v: str) -> str:
        try:
            ipaddress.IPv4Address(v.strip())
            return v.strip()
        except ValueError as err:
            raise ValueError(f"Invalid BGP network address '{v}': {err}")

    @field_validator("mask")
    @classmethod
    def validate_bgp_mask(cls, v: str) -> str:
        try:
            ipaddress.IPv4Network(f"0.0.0.0/{v.strip()}")
            return v.strip()
        except ValueError as err:
            raise ValueError(f"Invalid BGP subnet mask '{v}': {err}")


class BGPConfig(BaseModel):
    """BGP routing process parameters (RFC 4271)."""

    local_as: int = Field(..., ge=1, le=4294967295, description="Local Autonomous System Number", examples=[65001])
    router_id: Optional[str] = Field(None, description="BGP 32-bit Router ID in dotted decimal")
    neighbors: List[BGPNeighborConfig] = Field(default_factory=list, description="Configured BGP neighbors")
    networks: List[BGPNetworkConfig] = Field(default_factory=list, description="Networks advertised into BGP")

    @field_validator("router_id")
    @classmethod
    def validate_bgp_router_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None
        try:
            ipaddress.IPv4Address(clean)
            return clean
        except ValueError as err:
            raise ValueError(f"Invalid BGP router ID '{clean}': {err}")

    @model_validator(mode="after")
    def validate_ebgp_neighbors(self) -> "BGPConfig":
        if not self.neighbors:
            raise ValueError("BGP configuration must include at least one configured neighbor.")
        for neighbor in self.neighbors:
            if neighbor.remote_as == self.local_as:
                raise ValueError(
                    f"Neighbor {neighbor.ip_address} has remote-as {neighbor.remote_as} identical to local-as {self.local_as}. "
                    "eBGP requires distinct Autonomous System Numbers (remote-as != local-as)."
                )
        return self


class ConfigGenerationRequest(BaseModel):
    """Complete request to generate Cisco IOS device configurations."""

    network_name: str = Field(
        "Campus-LAN-Core",
        min_length=1,
        description="Parent network domain identifier",
        examples=["Campus-LAN-Core"],
    )
    hostname: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="Target device hostname",
        examples=["R1-Core"],
    )
    device_type: str = Field(
        "router",
        description="Device platform classification: 'router' or 'switch'",
        examples=["router"],
    )
    device_role: str = Field(
        "core",
        description="Architectural tier: 'core', 'distribution', 'access', 'edge', 'gateway'",
        examples=["core"],
    )
    target_platform: Optional[str] = Field(
        None,
        description="Target platform profile: 'cisco_catalyst_legacy_l3' (multi-encapsulation), 'cisco_catalyst_fixed_dot1q' (fixed 802.1Q), or 'generic'",
        examples=["cisco_catalyst_fixed_dot1q"],
    )
    ios_version: Optional[str] = Field(
        None,
        description="Explicit Cisco IOS / IOS-XE release version (e.g., '15.6(2)T', '17.3.4'). Omitted if unspecified.",
    )
    ip_domain_name: Optional[str] = Field(
        None,
        description="IP domain name required for cryptographic RSA key generation (e.g. 'netarchitect.edu')",
        examples=["netarchitect.edu"],
    )
    ssh_version: Optional[int] = Field(
        None,
        ge=1,
        le=2,
        description="Cisco IOS SSH protocol version (1 or 2)",
        examples=[2],
    )
    interfaces: List[InterfaceConfig] = Field(
        default_factory=list,
        description="List of physical and logical interface configurations",
    )
    vlans: List[VLANConfig] = Field(
        default_factory=list,
        description="List of declared IEEE 802.1Q VLANs",
    )
    routing_architecture: Optional[str] = Field(
        None,
        description="Routing architecture archetype: 'Single-Area OSPF (Area 0)', 'Multi-Area OSPF', 'eBGP'",
    )
    ospf: Optional[OSPFConfig] = Field(None, description="OSPF routing protocol parameters")
    bgp: Optional[BGPConfig] = Field(None, description="BGP routing protocol parameters")
    default_gateway: Optional[str] = Field(
        None,
        description="Management default gateway (e.g. for Layer 2 switches)",
        examples=["192.168.1.1"],
    )
    optional_settings: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Device-specific parameters (e.g. service timestamps, banner)",
    )

    # Integration references from upstream engines
    media_recommendation: Optional[Dict[str, Any]] = Field(
        None,
        description="Outputs from MediaEngine if linked",
    )
    vlsm_allocation: Optional[Dict[str, Any]] = Field(
        None,
        description="Outputs from VLSMEngine if linked",
    )
    routing_recommendation: Optional[Dict[str, Any]] = Field(
        None,
        description="Outputs from RoutingEngine if linked",
    )

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Hostname cannot be empty.")
        if not re.match(r"^[A-Za-z0-9_-]+$", clean):
            raise ValueError(f"Hostname '{clean}' contains invalid characters. Use alphanumeric, hyphen, or underscore.")
        return clean

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean in {"router", "cisco_router", "rtr"}:
            return "router"
        elif clean in {"switch", "cisco_switch", "sw", "layer2_switch", "l2_switch"}:
            return "switch"
        raise ValueError(f"Device type must be 'router' or 'switch'; got '{v}'.")

    @field_validator("default_gateway")
    @classmethod
    def validate_gateway(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None
        try:
            ipaddress.IPv4Address(clean)
            return clean
        except ValueError as err:
            raise ValueError(f"Invalid default gateway IPv4 address '{clean}': {err}")

    @model_validator(mode="after")
    def validate_cross_configuration_constraints(self) -> "ConfigGenerationRequest":
        # 1. Check for duplicate interface names
        seen_interfaces = set()
        for iface in self.interfaces:
            normalized_name = iface.name.lower()
            if normalized_name in seen_interfaces:
                raise ValueError(f"Duplicate interface configuration detected for '{iface.name}'.")
            seen_interfaces.add(normalized_name)

        # 2. Check for duplicate VLAN IDs
        seen_vlans = set()
        declared_vlan_ids = set()
        for vlan in self.vlans:
            if vlan.vlan_id in seen_vlans:
                raise ValueError(f"Duplicate VLAN ID detected: VLAN {vlan.vlan_id} ('{vlan.name}').")
            seen_vlans.add(vlan.vlan_id)
            declared_vlan_ids.add(vlan.vlan_id)

        # 3. Check access port and trunk allowed VLAN references against declared VLANs
        for iface in self.interfaces:
            if iface.mode == "access" and iface.access_vlan is not None:
                if iface.access_vlan not in declared_vlan_ids and declared_vlan_ids:
                    raise ValueError(
                        f"Interface '{iface.name}' is assigned access VLAN {iface.access_vlan}, "
                        f"which is not among the declared VLANs: {sorted(list(declared_vlan_ids))}."
                    )
            if iface.mode == "trunk" and iface.allowed_vlans:
                if declared_vlan_ids:
                    missing_vlans = [vid for vid in iface.allowed_vlans if vid not in declared_vlan_ids]
                    if missing_vlans:
                        raise ValueError(
                            f"Interface '{iface.name}' trunk allows VLANs {missing_vlans} "
                            f"that are not declared on this device."
                        )

        # 4. Credential / Secret safety check
        prohibited_keywords = ["password", "secret", "cisco123", "admin123", "enable secret"]
        if self.optional_settings:
            for k, v in self.optional_settings.items():
                k_lower = str(k).lower()
                v_lower = str(v).lower()
                for keyword in prohibited_keywords:
                    if keyword in k_lower or keyword in v_lower:
                        raise ValueError(
                            f"Plaintext credential or secret keyword '{keyword}' detected in optional_settings. "
                            "For academic safety, configurations cannot store or export credentials."
                        )

        return self


class ConfigCommandExplanation(BaseModel):
    """Academic explanation of a generated Cisco IOS configuration command or section."""

    command: str = Field(..., description="Cisco IOS CLI command or block header")
    section: str = Field(..., description="Configuration section (e.g., Basic, VLAN, Layer 3, OSPF, BGP)")
    purpose: str = Field(..., description="Technical and academic justification for this command")
    standard_ref: Optional[str] = Field(None, description="Governing RFC, IEEE standard, or Cisco guideline")


class ConfigGenerationResponse(BaseModel):
    """Complete generated device configuration response."""

    config_id: str = Field(..., description="Unique UUID identifier for this configuration run")
    network_name: str = Field(..., description="Name of the evaluated network domain")
    hostname: str = Field(..., description="Configured device hostname")
    device_type: str = Field(..., description="'router' or 'switch'")
    device_role: str = Field(..., description="Device role in network hierarchy")
    generation_timestamp: str = Field(..., description="UTC ISO timestamp of configuration generation")
    configuration_sections: Dict[str, str] = Field(
        ...,
        description="Individual modular configuration sections",
    )
    complete_config_text: str = Field(
        ...,
        description="Full, concatenated Cisco IOS configuration script ready for review",
    )
    validation_status: str = Field(
        ...,
        description="'VALID' or 'VALID_WITH_WARNINGS'",
    )
    validation_scope: str = Field(
        "Input and Topology Constraint Validation",
        description="Clarification that schema/topological constraints are verified; hardware-level syntax parsing remains pending.",
    )
    warnings_and_assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions, caveats, and items requiring manual administrator review",
    )
    command_explanations: List[ConfigCommandExplanation] = Field(
        default_factory=list,
        description="Step-by-step academic justifications for generated CLI commands",
    )
    explainability_record_id: Optional[str] = Field(
        None,
        description="UUID reference to the ExplainabilityEngine audit record",
    )
    export_filename: str = Field(
        ...,
        description="Safe filename in backend/exports/ (e.g., R1-Core_abc12345.cfg)",
    )
    export_file_path: Optional[str] = Field(
        None,
        description="Relative system path to the exported configuration file",
    )
    download_url: Optional[str] = Field(
        None,
        description="API endpoint to download the generated configuration",
    )
    safety_notice: str = Field(
        ...,
        description="Academic simulation disclaimer and manual review safety notice",
    )


# Backward compatibility aliases
DeviceConfigGenerationRequest = ConfigGenerationRequest
DeviceConfigGenerationResponse = ConfigGenerationResponse
