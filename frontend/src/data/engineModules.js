/**
 * Architecture modules representing the core computational engines of NetArchitect.
 */
export const ENGINE_MODULES = [
  {
    name: 'Media Recommendation Engine',
    file: 'engines/media_engine.py',
    purpose: 'Selects Layer 1 physical transmission media (Twisted Pair, Optical Fiber, Wireless) based on distance, throughput, and noise.',
    status: 'Scaffolded',
    layer: 'Layer 1 Physical',
  },
  {
    name: 'VLSM & Subnetting Engine',
    file: 'engines/vlsm_engine.py',
    purpose: 'Performs Variable Length Subnet Masking and CIDR address space partitioning (RFC 1878, RFC 4632).',
    status: 'Scaffolded',
    layer: 'Layer 3 Network',
  },
  {
    name: 'Routing Protocol Engine',
    file: 'engines/routing_engine.py',
    purpose: 'Evaluates topology scale and convergence requirements to recommend IGP (OSPF) or EGP (BGP).',
    status: 'Scaffolded',
    layer: 'Layer 3 Routing',
  },
  {
    name: 'Explainability Engine',
    file: 'engines/explainability_engine.py',
    purpose: 'Audit logs engineering rationale, constraints, recommendations, and RFC citations for academic defense.',
    status: 'Scaffolded',
    layer: 'Cross-cutting',
  },
  {
    name: 'Device Configuration Generator',
    file: 'engines/config_generator.py',
    purpose: 'Synthesizes deployable CLI configuration scripts (e.g. Cisco IOS) from computed models.',
    status: 'Scaffolded',
    layer: 'Management / CLI',
  },
]
