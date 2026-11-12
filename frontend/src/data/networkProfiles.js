/**
 * Static metadata for the three mandatory network profiles in NetArchitect.
 */
export const NETWORK_PROFILES = [
  {
    id: 'campus_lan',
    name: 'Campus LAN',
    scope: 'Local Area Network (< 2 km)',
    bandwidth: '1 Gbps - 10 Gbps',
    latency: '< 5 ms',
    primaryMedia: 'Copper Cat6/Cat6a, Multi-mode/Single-mode Fiber',
    routing: 'OSPF (Single/Multi-Area)',
    addressing: 'RFC 1918 Private IPv4 with VLSM',
    badgeColor: 'blue',
  },
  {
    id: 'metro_man',
    name: 'Metro MAN',
    scope: 'Metropolitan Area Network (5 - 50 km)',
    bandwidth: '1 Gbps - 40 Gbps',
    latency: '5 - 20 ms',
    primaryMedia: 'Single-mode Fiber (OS2), Carrier Ethernet',
    routing: 'Multi-area OSPF / IS-IS / Carrier Peering',
    addressing: 'Hierarchical Regional CIDR Aggregation',
    badgeColor: 'purple',
  },
  {
    id: 'global_wan',
    name: 'Global WAN',
    scope: 'Wide Area Network (> 100 km)',
    bandwidth: '100 Mbps - 10 Gbps',
    latency: '30 - 150+ ms',
    primaryMedia: 'Subsea Fiber, Leased Lines, SD-WAN Tunnels',
    routing: 'BGP-4 (Border Gateway Protocol, RFC 4271)',
    addressing: 'Public AS Numbers & NAT/PAT Edge Addressing',
    badgeColor: 'green',
  },
]
