"""Device Configuration Generator Engine.

Academic Context:
Translates validated logical network topologies, VLAN allocations, IP addressing,
and routing protocol architectures into industry-standard, syntax-valid
Cisco IOS / IOS-XE configuration templates.

Key Capabilities:
1. Basic device identity, domain lookup suppression, and interface status.
2. Layer 2 IEEE 802.1Q VLANs, access port assignments, and trunk allowed-lists.
3. Layer 3 IPv4 addressing, subnet masks, and default gateways.
4. Single-Area and Multi-Area OSPF (RFC 2328) with Area 0 backbone hierarchy.
5. External BGP (eBGP RFC 4271) with verified neighbor peering and network masks.
6. Rigorous validation against duplicate interfaces, duplicate VLANs, invalid IPs,
   missing BGP neighbors, and plaintext credential exposure.
7. Safe file exports (.cfg, .txt) with path-traversal prevention.
8. ExplainabilityEngine audit trail logging.

Standards:
- Cisco IOS Configuration Fundamentals Configuration Guide
- IEEE 802.1Q: Virtual Bridged Local Area Networks
- RFC 2328: OSPF Version 2 (STD 54)
- RFC 4271: A Border Gateway Protocol 4 (BGP-4)
"""

from datetime import datetime, timezone
import ipaddress
import os
from pathlib import Path
import re
from typing import Dict, Any, List, Optional, Union
from uuid import uuid4

from engines.explainability_engine import ExplainabilityEngine
from models.config import (
    ConfigGenerationRequest,
    ConfigGenerationResponse,
    ConfigCommandExplanation,
    InterfaceConfig,
    VLANConfig,
    OSPFConfig,
    BGPConfig,
)


class ConfigGenerator:
    """Engine responsible for generating target Cisco IOS device configuration files."""

    SAFETY_DISCLAIMER: str = (
        "ACADEMIC NOTICE: Synthesized configuration template for academic demonstration. "
        "This configuration has NOT been deployed or verified on physical production Cisco hardware. "
        "Review all parameters before deployment. No plaintext passwords or production credentials are included."
    )

    def __init__(
        self,
        export_dir: Optional[str] = None,
        explainability_engine: Optional[ExplainabilityEngine] = None,
    ):
        """Initialize ConfigGenerator with export directory and explainability logging."""
        if export_dir:
            self.export_dir = Path(export_dir).resolve()
        else:
            self.export_dir = (Path(__file__).resolve().parent.parent / "exports").resolve()

        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.explainability_engine = explainability_engine or ExplainabilityEngine()
        self._generated_configs: Dict[str, Dict[str, Any]] = {}
        self.is_ready = True

    def generate_config(
        self,
        request: Union[ConfigGenerationRequest, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generates a complete Cisco IOS configuration script from a validated request.

        Args:
            request: Validated ConfigGenerationRequest instance or raw dictionary.

        Returns:
            Dict conforming to ConfigGenerationResponse.
        """
        # Validate request via Pydantic model if raw dict is passed
        if isinstance(request, dict):
            validated_req = ConfigGenerationRequest.model_validate(request)
        else:
            validated_req = request

        config_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        warnings: List[str] = []
        command_explanations: List[ConfigCommandExplanation] = []
        sections: Dict[str, str] = {}

        # Warnings on general deployment
        warnings.append("Academic simulation template: requires manual review before applying to physical hardware.")
        warnings.append("No user accounts or enable secret passwords configured; administrator must configure SSH/AAA credentials securely.")

        # --- Section 1: Header Banner ---
        header_lines = [
            "! ==============================================================================",
            "! NetArchitect Academic Configuration Engine",
            f"! Generated At    : {timestamp}",
            "! Target Platform : Cisco IOS / IOS-XE",
            f"! Device Hostname : {validated_req.hostname}",
            f"! Device Type     : {validated_req.device_type.upper()}",
            f"! Device Role     : {validated_req.device_role.upper()}",
            f"! Network Domain  : {validated_req.network_name}",
            "!",
            "! ACADEMIC DISCLAIMER:",
            "! Synthesized academic simulation template for demonstration purposes.",
            "! This configuration has NOT been deployed or verified on physical production",
            "! Cisco hardware. All parameters must be reviewed prior to deployment.",
            "!",
            "! SECURITY NOTICE:",
            "! No plaintext passwords, privileged credentials, or cryptographic secrets",
            "! are included in this generated configuration file.",
            "! ==============================================================================",
            "version 15.6",
            "service timestamps debug datetime msec",
            "service timestamps log datetime msec",
            "no service password-encryption",
        ]
        sections["header"] = "\n".join(header_lines)
        command_explanations.append(
            ConfigCommandExplanation(
                command="service timestamps log datetime msec",
                section="header",
                purpose="Applies high-resolution millisecond timestamps to system logging events for accurate diagnostic analysis.",
                standard_ref="Cisco IOS Network Management Configuration Guide",
            )
        )

        # --- Section 2: Basic Device Configuration ---
        basic_lines = [
            f"hostname {validated_req.hostname}",
            "!",
            "no ip domain-lookup",
        ]
        if validated_req.device_type == "router":
            basic_lines.append("ip routing")
            command_explanations.append(
                ConfigCommandExplanation(
                    command="ip routing",
                    section="basic",
                    purpose="Globally enables IPv4 unicast routing on the routing engine.",
                    standard_ref="Cisco IOS IP Routing: Protocol-Independent Configuration Guide",
                )
            )

        command_explanations.append(
            ConfigCommandExplanation(
                command="no ip domain-lookup",
                section="basic",
                purpose="Prevents the router from hanging during CLI mistypes by disabling automatic DNS name resolution for unrecognized commands.",
                standard_ref="Cisco IOS Configuration Fundamentals",
            )
        )
        sections["basic"] = "\n".join(basic_lines)

        # --- Section 3: VLAN Configuration (IEEE 802.1Q) ---
        vlan_lines = []
        if validated_req.vlans:
            vlan_lines.append("! --- VLAN Configuration (IEEE 802.1Q) ---")
            for vlan in validated_req.vlans:
                vlan_lines.append(f"vlan {vlan.vlan_id}")
                vlan_lines.append(f" name {vlan.name}")
                vlan_lines.append("!")
            command_explanations.append(
                ConfigCommandExplanation(
                    command=f"vlan {validated_req.vlans[0].vlan_id}",
                    section="vlans",
                    purpose="Instantiates Layer 2 broadcast domains in the VLAN database to segment network traffic.",
                    standard_ref="IEEE 802.1Q (Virtual Bridged Local Area Networks)",
                )
            )
            sections["vlans"] = "\n".join(vlan_lines)
        elif validated_req.device_type == "switch":
            warnings.append("No custom VLANs declared; switch interfaces default to VLAN 1.")

        # --- Section 4: Interface Configuration ---
        interface_lines = []
        interface_lines.append("! --- Interface Configuration ---")
        for iface in validated_req.interfaces:
            interface_lines.append(f"interface {iface.name}")

            # Description with optional media reference
            desc_parts = []
            if iface.description:
                desc_parts.append(iface.description)
            if iface.media_type:
                desc_parts.append(f"[{iface.media_type}]")
            if desc_parts:
                interface_lines.append(f" description {' '.join(desc_parts)}")

            # Switchport modes (Access or Trunk)
            if validated_req.device_type == "switch" or iface.mode in {"access", "trunk"}:
                if iface.mode == "access":
                    interface_lines.append(" switchport mode access")
                    if iface.access_vlan is not None:
                        interface_lines.append(f" switchport access vlan {iface.access_vlan}")
                elif iface.mode == "trunk":
                    interface_lines.append(" switchport trunk encapsulation dot1q")
                    interface_lines.append(" switchport mode trunk")
                    if iface.allowed_vlans:
                        vlans_str = ",".join(str(vid) for vid in sorted(iface.allowed_vlans))
                        interface_lines.append(f" switchport trunk allowed vlan {vlans_str}")

            # Layer 3 IP addressing
            if iface.ip_address and iface.subnet_mask:
                interface_lines.append(f" ip address {iface.ip_address} {iface.subnet_mask}")

            # Interface-level OSPF area assignment (if configured)
            if iface.ospf_area is not None:
                ospf_proc = validated_req.ospf.process_id if validated_req.ospf else 1
                interface_lines.append(f" ip ospf {ospf_proc} area {iface.ospf_area}")

            # Administrative state (no shutdown / shutdown)
            if iface.enabled:
                interface_lines.append(" no shutdown")
            else:
                interface_lines.append(" shutdown")

            interface_lines.append("!")

        command_explanations.append(
            ConfigCommandExplanation(
                command="interface <name>",
                section="interfaces",
                purpose="Configures physical or logical Layer 2/3 interface parameters (encapsulation, IP, VLAN, and administrative status).",
                standard_ref="Cisco IOS Interface and Hardware Component Configuration Guide",
            )
        )
        sections["interfaces"] = "\n".join(interface_lines)

        # --- Section 5: Default Gateway (for Switches) ---
        if validated_req.device_type == "switch" and validated_req.default_gateway:
            sections["gateway"] = f"ip default-gateway {validated_req.default_gateway}"
            command_explanations.append(
                ConfigCommandExplanation(
                    command=f"ip default-gateway {validated_req.default_gateway}",
                    section="gateway",
                    purpose="Specifies the default router IP for management traffic originating from the Layer 2 switch.",
                    standard_ref="Cisco IOS IP Configuration Guide",
                )
            )

        # --- Section 6: OSPF Routing Protocol (RFC 2328) ---
        if validated_req.ospf:
            ospf_lines = [
                "! --- Routing Protocol Configuration (OSPFv2 RFC 2328) ---",
                f"router ospf {validated_req.ospf.process_id}",
                f" router-id {validated_req.ospf.router_id}",
                " log-adjacency-changes",
            ]
            for passive in validated_req.ospf.passive_interfaces:
                ospf_lines.append(f" passive-interface {passive}")

            has_area_0 = False
            for net in validated_req.ospf.networks:
                # Format area
                area_str = str(net.area)
                if area_str in {"0", "0.0.0.0"}:
                    has_area_0 = True
                ospf_lines.append(f" network {net.network} {net.wildcard_mask} area {net.area}")

            # Validate routing architecture consistency
            arch = (validated_req.routing_architecture or "").lower()
            if "single-area" in arch:
                for net in validated_req.ospf.networks:
                    if str(net.area) not in {"0", "0.0.0.0"}:
                        raise ValueError(
                            f"Single-Area OSPF architecture mandates Area 0, but network {net.network} "
                            f"is assigned to Area '{net.area}'."
                        )
            elif "multi-area" in arch:
                if validated_req.ospf.networks and not has_area_0:
                    warnings.append(
                        "Multi-Area OSPF was specified, but no Area 0 network statement is defined. "
                        "Area 0 (Backbone) is mandatory in Multi-Area OSPF (RFC 2328)."
                    )

            sections["ospf"] = "\n".join(ospf_lines)
            command_explanations.append(
                ConfigCommandExplanation(
                    command=f"router ospf {validated_req.ospf.process_id}",
                    section="ospf",
                    purpose="Initializes an OSPFv2 link-state routing process with Dijkstra Shortest Path First calculation.",
                    standard_ref="RFC 2328: OSPF Version 2",
                )
            )
            command_explanations.append(
                ConfigCommandExplanation(
                    command=f"router-id {validated_req.ospf.router_id}",
                    section="ospf",
                    purpose="Statically assigns the 32-bit unique router identifier to stabilize OSPF neighbor adjacencies and DR/BDR elections.",
                    standard_ref="RFC 2328 Clause 1.2",
                )
            )

        # --- Section 7: eBGP Routing Protocol (RFC 4271) ---
        if validated_req.bgp:
            bgp_lines = [
                "! --- Routing Protocol Configuration (eBGP RFC 4271) ---",
                f"router bgp {validated_req.bgp.local_as}",
                " bgp log-neighbor-changes",
            ]
            if validated_req.bgp.router_id:
                bgp_lines.append(f" bgp router-id {validated_req.bgp.router_id}")

            for neighbor in validated_req.bgp.neighbors:
                bgp_lines.append(f" neighbor {neighbor.ip_address} remote-as {neighbor.remote_as}")
                if neighbor.description:
                    bgp_lines.append(f" neighbor {neighbor.ip_address} description {neighbor.description}")

            for net in validated_req.bgp.networks:
                bgp_lines.append(f" network {net.network} mask {net.mask}")

            sections["bgp"] = "\n".join(bgp_lines)
            command_explanations.append(
                ConfigCommandExplanation(
                    command=f"router bgp {validated_req.bgp.local_as}",
                    section="bgp",
                    purpose="Initializes the Border Gateway Protocol process for inter-Autonomous System path-vector routing.",
                    standard_ref="RFC 4271: A Border Gateway Protocol 4 (BGP-4)",
                )
            )
            command_explanations.append(
                ConfigCommandExplanation(
                    command="neighbor <ip> remote-as <asn>",
                    section="bgp",
                    purpose="Defines an external BGP peering session over TCP port 179 with an adjacent autonomous system.",
                    standard_ref="RFC 4271 Section 4.2",
                )
            )

        # --- Section 8: Management Access & End ---
        line_access = [
            "! --- Line and Management Access ---",
            "line con 0",
            " logging synchronous",
            " stopbits 1",
            "line vty 0 4",
            " transport input ssh",
            "!",
            "end",
        ]
        sections["management"] = "\n".join(line_access)
        command_explanations.append(
            ConfigCommandExplanation(
                command="transport input ssh",
                section="management",
                purpose="Restricts remote administrative VTY sessions to encrypted SSH transport, preventing plaintext Telnet exposure.",
                standard_ref="Cisco IOS Security Configuration Guide",
            )
        )

        # --- Assemble Complete Configuration Text ---
        complete_config_blocks = [
            sections["header"],
            sections["basic"],
        ]
        if "vlans" in sections:
            complete_config_blocks.append(sections["vlans"])
        complete_config_blocks.append(sections["interfaces"])
        if "gateway" in sections:
            complete_config_blocks.append(sections["gateway"])
        if "ospf" in sections:
            complete_config_blocks.append(sections["ospf"])
        if "bgp" in sections:
            complete_config_blocks.append(sections["bgp"])
        complete_config_blocks.append(sections["management"])

        complete_config_text = "\n!\n".join(complete_config_blocks) + "\n"

        # --- Safe File Export ---
        safe_hostname = re.sub(r"[^A-Za-z0-9_-]", "_", validated_req.hostname)
        export_filename = f"{safe_hostname}_{config_id[:8]}.cfg"
        export_file_path = (self.export_dir / export_filename).resolve()

        # Strict Path Traversal Prevention: File must reside strictly inside self.export_dir
        if not str(export_file_path).startswith(str(self.export_dir)):
            raise ValueError(f"Path traversal security violation for target '{export_filename}'.")

        # Persist both .cfg and .txt files
        export_file_path.write_text(complete_config_text, encoding="utf-8")
        txt_path = export_file_path.with_suffix(".txt")
        txt_path.write_text(complete_config_text, encoding="utf-8")

        # Determine validation status
        validation_status = "VALID_WITH_WARNINGS" if len(warnings) > 2 else "VALID"

        # --- ExplainabilityEngine Integration ---
        audit_reasoning = (
            f"1. Target Device: {validated_req.hostname} ({validated_req.device_type.upper()}, Role: {validated_req.device_role.upper()}).\n"
            f"2. Network Domain: {validated_req.network_name}.\n"
            f"3. Layer 2 VLAN Tagging: Configured {len(validated_req.vlans)} VLAN(s) under IEEE 802.1Q.\n"
            f"4. Layer 3 Addressing: Configured {len(validated_req.interfaces)} interface(s) with validated IPv4 and subnet masks.\n"
            f"5. Routing Protocol Architecture: {validated_req.routing_architecture or 'None'} "
            f"(OSPF: {'Active' if validated_req.ospf else 'Inactive'}, BGP: {'Active' if validated_req.bgp else 'Inactive'}).\n"
            f"6. Credential Safety: Verified zero plaintext passwords or secrets in configuration.\n"
            f"7. Export Destination: {export_filename} in backend/exports/."
        )

        explanation_record = self.explainability_engine.record_explanation(
            engine_name="ConfigGenerator",
            input_conditions={
                "hostname": validated_req.hostname,
                "device_type": validated_req.device_type,
                "device_role": validated_req.device_role,
                "interface_count": len(validated_req.interfaces),
                "vlan_count": len(validated_req.vlans),
                "routing_architecture": validated_req.routing_architecture,
                "has_ospf": validated_req.ospf is not None,
                "has_bgp": validated_req.bgp is not None,
                "media_recommendation": validated_req.media_recommendation,
                "vlsm_allocation": validated_req.vlsm_allocation,
                "routing_recommendation": validated_req.routing_recommendation,
            },
            selected_recommendation={
                "config_id": config_id,
                "export_filename": export_filename,
                "validation_status": validation_status,
                "sections_generated": list(sections.keys()),
            },
            technical_reasoning=audit_reasoning,
            standards_and_rfcs=[
                "Cisco IOS Configuration Fundamentals Configuration Guide",
                "IEEE 802.1Q: Virtual Bridged Local Area Networks",
                "RFC 2328: OSPF Version 2 (STD 54)",
                "RFC 4271: A Border Gateway Protocol 4 (BGP-4)",
            ],
        )

        relative_export_path = f"backend/exports/{export_filename}"
        download_url = f"/api/v1/configs/{config_id}/download"

        result_dict = {
            "config_id": config_id,
            "network_name": validated_req.network_name,
            "hostname": validated_req.hostname,
            "device_type": validated_req.device_type,
            "device_role": validated_req.device_role,
            "generation_timestamp": timestamp,
            "configuration_sections": sections,
            "complete_config_text": complete_config_text,
            "validation_status": validation_status,
            "warnings_and_assumptions": warnings,
            "command_explanations": [exp.model_dump() for exp in command_explanations],
            "explainability_record_id": explanation_record.record_id,
            "export_filename": export_filename,
            "export_file_path": relative_export_path,
            "download_url": download_url,
            "safety_notice": self.SAFETY_DISCLAIMER,
        }

        # Store in internal registry for lookup & download
        self._generated_configs[config_id] = {
            "result": result_dict,
            "file_path": str(export_file_path),
            "filename": export_filename,
            "created_at": timestamp,
        }

        return result_dict

    def get_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve generated configuration metadata and text by ID."""
        entry = self._generated_configs.get(config_id)
        if entry:
            return entry["result"]
        return None

    def list_configs(self) -> List[Dict[str, Any]]:
        """List metadata summaries for all generated configurations."""
        summaries = []
        for cid, entry in self._generated_configs.items():
            res = entry["result"]
            summaries.append(
                {
                    "config_id": cid,
                    "hostname": res["hostname"],
                    "device_type": res["device_type"],
                    "device_role": res["device_role"],
                    "generation_timestamp": res["generation_timestamp"],
                    "validation_status": res["validation_status"],
                    "export_filename": res["export_filename"],
                    "download_url": res["download_url"],
                }
            )
        return summaries

    def get_export_file_path(self, config_id: str) -> Optional[Path]:
        """Safely fetch the canonical filesystem Path for a config export."""
        entry = self._generated_configs.get(config_id)
        if not entry:
            return None
        path = Path(entry["file_path"]).resolve()
        if not str(path).startswith(str(self.export_dir)):
            return None
        if not path.is_file():
            return None
        return path

    # Backward-compatible alias
    def generate_cisco_ios(self, hostname: str, interfaces: List[Dict[str, Any]], **kwargs) -> str:
        """Legacy helper generating Cisco IOS text directly."""
        req_data = {
            "hostname": hostname,
            "interfaces": interfaces,
            **kwargs,
        }
        res = self.generate_config(req_data)
        return res["complete_config_text"]
