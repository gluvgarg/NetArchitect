"""Pydantic models for Device Configuration Generation."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class InterfaceConfig(BaseModel):
    """Interface configuration parameter model."""
    name: str = Field(..., description="Interface name (e.g. GigabitEthernet0/0/0)")
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    description: Optional[str] = None
    vlan_id: Optional[int] = None
    is_trunk: bool = False
    enabled: bool = True


class ConfigGenerationRequest(BaseModel):
    """Request to generate device CLI configuration."""
    hostname: str = Field(..., description="Target device hostname")
    device_type: str = Field("cisco_router", description="'cisco_router', 'cisco_switch', 'generic_l3'")
    interfaces: List[InterfaceConfig] = Field(default_factory=list)
    routing_protocol: Optional[str] = None
    routing_config: Optional[Dict[str, Any]] = None


class ConfigGenerationResponse(BaseModel):
    """Generated device configuration output."""
    hostname: str
    target_platform: str
    configuration_script: str
    export_filename: str
