"""Routing Protocol Recommendation Engine.

Academic Context:
Analyzes network topology scope, autonomous system boundaries, subnet scale,
and hierarchy requirements to recommend deterministic routing architectures:
1. Single-Area OSPF (Area 0) for small-to-medium single-AS internal networks (< 50 subnets).
2. Multi-Area OSPF for partitioned single-AS networks requiring hierarchical area isolation.
3. eBGP for inter-Autonomous System routing and external provider peering.
4. Design Review / Validation diagnostics when topology inputs are contradictory or underspecified.

Standards & References:
- RFC 2328: OSPF Version 2 (STD 54) - Link-state routing, Dijkstra SPF algorithm, Area hierarchy.
- RFC 4271: A Border Gateway Protocol 4 (BGP-4) - Path-vector mechanics, AS_PATH loop prevention.
"""

from typing import Dict, Any, Optional, List
from engines.explainability_engine import ExplainabilityEngine


class RoutingEngine:
    """Engine responsible for deterministic routing architecture recommendations."""

    # Operational/academic threshold for single-area link-state scalability
    SINGLE_AREA_MAX_SUBNETS: int = 50

    def __init__(self, explainability_engine: Optional[ExplainabilityEngine] = None):
        """Initialize the RoutingEngine with an optional ExplainabilityEngine."""
        self.explainability_engine = explainability_engine or ExplainabilityEngine()
        self.is_ready = True

    def recommend_routing(
        self,
        network_name: str,
        autonomous_system_count: int = 1,
        subnet_count: int = 1,
        site_count: int = 1,
        has_external_as_boundary: bool = False,
        ospf_areas_required: Optional[int] = None,
        topology_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates optimal routing protocol architecture using deterministic precedence rules.

        Precedence Hierarchy:
        --------------------
        1. Contradiction Detection: Identifies conflicting inputs (e.g. AS > 1 without external boundary).
        2. Rule 1 (Inter-AS / External Boundary Precedence): If AS > 1 or external boundary is True -> eBGP.
        3. Rule 2 (Multi-Area OSPF Precedence): If AS == 1 and ospf_areas_required > 1 -> Multi-Area OSPF.
        4. Rule 3 (Single-Area OSPF Area 0 Precedence): If AS == 1, subnets < 50, and areas in (None, 1) -> Single-Area OSPF.
        5. Rule 4 (Scale Boundary Review): If AS == 1, subnets >= 50, and areas is None -> Design Review Required.

        Args:
            network_name: Name or identifier of target network.
            autonomous_system_count: Number of autonomous systems (must be >= 1).
            subnet_count: Total number of Layer 3 subnets in the domain (must be >= 1).
            site_count: Physical geographic sites/campuses (must be >= 1).
            has_external_as_boundary: True if network peers with external AS / ISP.
            ospf_areas_required: Explicit count of OSPF areas if planned.
            topology_description: Optional narrative context.

        Returns:
            Dict conforming to RoutingRecommendationResponse model.
        """
        # --- 1. Input Validation ---
        if not isinstance(network_name, str) or not network_name.strip():
            raise ValueError("Network name must be a non-empty string.")

        if not isinstance(autonomous_system_count, int) or autonomous_system_count < 1:
            raise ValueError("Autonomous system count must be a positive integer (>= 1).")

        if not isinstance(subnet_count, int) or subnet_count < 1:
            raise ValueError("Subnet count must be a positive integer (>= 1).")

        if not isinstance(site_count, int) or site_count < 1:
            raise ValueError("Site count must be a positive integer (>= 1).")

        if ospf_areas_required is not None:
            if not isinstance(ospf_areas_required, int) or ospf_areas_required < 1:
                raise ValueError("OSPF area count must be a positive integer (>= 1).")

        clean_network_name = network_name.strip()

        # --- 2. Deterministic Decision Logic & Precedence ---

        # Precedence 1: Contradiction Check (AS > 1 but has_external_as_boundary is False)
        if autonomous_system_count > 1 and not has_external_as_boundary:
            rule_selected = "Contradiction: Multiple ASes without External Boundary"
            recommended_protocol = "Design Review Required: Contradictory Autonomous System Parameters"
            architecture_type = "Topology Validation Review"
            reason_for_selection = (
                f"Contradictory topology parameters detected: autonomous_system_count is {autonomous_system_count} (> 1), "
                f"but has_external_as_boundary is set to False. By definition (RFC 4271), distinct Autonomous Systems "
                f"represent independent routing administrative domains that communicate exclusively across external AS boundaries. "
                f"Either enable has_external_as_boundary (True) to establish inter-AS peering (eBGP), or consolidate the topology "
                f"into a single Autonomous System (autonomous_system_count: 1) if all nodes are managed under a single administrative authority."
            )
            as_info = {
                "as_count": autonomous_system_count,
                "is_multi_as": True,
                "has_external_boundary": False,
                "description": "Contradictory state: multiple Autonomous Systems specified without external boundary demarcation.",
            }
            ospf_info = None
            area_0_required = False
            abr_required = False
            requires_design_review = True
            routing_characteristics = [
                "Contradiction between autonomous_system_count and has_external_as_boundary.",
                "Multiple ASes cannot interconnect without an external peering boundary (RFC 4271).",
                "Internal link-state routing (OSPF) does not span multiple Autonomous Systems without mutual redistribution.",
            ]
            advantages = [
                "Early detection prevents invalid protocol deployment across mismatched administrative boundaries.",
            ]
            limitations = [
                "Cannot finalize routing architecture until the boundary relationship between the Autonomous Systems is clarified.",
            ]
            standards_and_rfcs = [
                "RFC 4271: A Border Gateway Protocol 4 (BGP-4)",
            ]
            alternatives_rejected = (
                "Single-Area OSPF and Multi-Area OSPF were rejected because multiple Autonomous Systems represent separate "
                "administrative domains. eBGP was not finalized because has_external_as_boundary was explicitly set to False."
            )

        # Precedence 2 (Rule 1): Inter-AS / External AS Boundary -> eBGP
        elif autonomous_system_count > 1 or has_external_as_boundary:
            rule_selected = "Rule 1: Inter-AS / External Boundary Precedence"
            recommended_protocol = "eBGP (External Border Gateway Protocol)"
            architecture_type = "Exterior Gateway Protocol (EGP) - Inter-AS Path-Vector"
            reason_for_selection = (
                f"An external Autonomous System routing boundary is present "
                f"(autonomous_system_count: {autonomous_system_count}, has_external_as_boundary: {has_external_as_boundary}). "
                f"eBGP (RFC 4271) is mandatory for exchanging reachability information between distinct Autonomous Systems. "
                f"Unlike link-state IGPs that share complete topology state, eBGP utilizes path vectors and the AS_PATH attribute "
                f"to prevent routing loops and enforce inter-organizational administrative policy. "
                f"Crucial Architectural Note: eBGP does NOT replace the internal routing protocol; an Interior Gateway Protocol "
                f"(such as Single-Area or Multi-Area OSPF) is still strictly required within each Autonomous System to distribute "
                f"internal subnets and resolve BGP recursive next-hop IP addresses."
            )
            as_info = {
                "as_count": autonomous_system_count,
                "is_multi_as": autonomous_system_count > 1,
                "has_external_boundary": has_external_as_boundary,
                "description": (
                    f"Inter-domain routing environment spanning {autonomous_system_count} Autonomous System(s) "
                    f"with active external boundary peering."
                ),
            }
            ospf_info = None
            area_0_required = False
            abr_required = False
            requires_design_review = False
            routing_characteristics = [
                "Path-vector routing protocol operating over reliable TCP transport (port 179).",
                "Loop prevention guaranteed across AS hops via the AS_PATH attribute (updates containing local ASN are rejected).",
                "Policy-driven route selection using BGP attributes: Weight, Local Preference, AS Path Length, Origin, and MED.",
                "Decoupled from internal physical topology; relies on underlying IGP for recursive next-hop reachability.",
            ]
            advantages = [
                "Massive scalability: powers the global Internet routing table across hundreds of thousands of prefixes.",
                "Granular policy enforcement: controls ingress/egress transit traffic between business entities.",
                "Administrative autonomy: internal topology changes inside an AS are completely hidden from external BGP peers.",
            ]
            limitations = [
                "Does NOT replace internal routing protocols (IGP); OSPF/IS-IS is still required internally.",
                "Slower convergence relative to link-state protocols due to TCP hold-timers and Minimum Route Advertisement Intervals (MRAI).",
                "Substantial memory requirements and operational policy configuration complexity.",
            ]
            standards_and_rfcs = [
                "RFC 4271: A Border Gateway Protocol 4 (BGP-4)",
                "RFC 1772: Application of the Border Gateway Protocol in the Internet",
            ]
            alternatives_rejected = (
                "OSPF (Single-Area or Multi-Area) was rejected as the primary recommendation for the inter-domain boundary "
                "because OSPF is an Interior Gateway Protocol designed for a single administrative domain; link-state flooding "
                "cannot scale or enforce policy across external Autonomous System boundaries. However, OSPF is still recommended "
                "for internal IGP routing inside each AS."
            )

        # Precedence 3 (Rule 2): Single AS with Explicit Multi-Area Requirement -> Multi-Area OSPF
        elif ospf_areas_required is not None and ospf_areas_required > 1:
            rule_selected = "Rule 2: Hierarchical IGP / Multi-Area OSPF Precedence"
            recommended_protocol = "Multi-Area OSPF"
            architecture_type = "Interior Gateway Protocol (IGP) - Hierarchical Link-State"
            reason_for_selection = (
                f"The network resides entirely within a single Autonomous System with {ospf_areas_required} internal OSPF areas "
                f"explicitly designated across {subnet_count} subnets and {site_count} site(s). "
                f"Multi-Area OSPF (RFC 2328) establishes a two-tier hierarchical routing domain. Area 0 (0.0.0.0) is the mandatory "
                f"backbone area to which all non-backbone areas must connect. Area Border Routers (ABRs) terminate area boundaries, "
                f"maintain isolated Link-State Databases (LSDBs) for each attached area, and inject Type 3 Summary LSAs across areas. "
                f"This hierarchy confines SPF recalculations to the area where a link flap occurs, preventing global routing instability."
            )
            as_info = {
                "as_count": 1,
                "is_multi_as": False,
                "has_external_boundary": False,
                "description": "Single enterprise/campus Autonomous System internal routing domain.",
            }
            area_roles = {
                "Area 0 (0.0.0.0)": "Core transit backbone interconnecting all peripheral areas; mandatory.",
            }
            for i in range(1, ospf_areas_required):
                area_roles[f"Area {i}"] = f"Standard non-backbone area {i} terminating at Area Border Routers (ABRs)."

            ospf_info = {
                "area_count": ospf_areas_required,
                "backbone_area": "Area 0 (0.0.0.0)",
                "requires_area_0": True,
                "requires_abr": True,
                "area_roles": area_roles,
                "design_notes": (
                    "All non-backbone areas must directly attach to contiguous Area 0. ABRs summarize routes "
                    "between areas using Type 3 Summary LSAs and restrict Type 1/2 LSAs to their local area."
                ),
            }
            area_0_required = True
            abr_required = True
            requires_design_review = False
            routing_characteristics = [
                "Two-tier hierarchical architecture centered on contiguous Area 0 (Backbone Area).",
                "Area Border Routers (ABRs) maintain separate LSDBs for each connected area.",
                "Type 1 (Router) and Type 2 (Network) LSAs are confined to local areas; Type 3 Summary LSAs advertise inter-area routes.",
                "Isolates Dijkstra SPF calculation overhead: link flaps in leaf areas do not trigger SPF runs in other areas.",
            ]
            advantages = [
                "High scalability: isolates topological churn and prevents global SPF storms.",
                "Route summarization at ABR boundaries dramatically reduces routing table sizes and memory consumption.",
                "Optimized for large enterprise campus and metropolitan area networks.",
            ]
            limitations = [
                "Strict hierarchical design rules: all non-backbone areas must physically or virtually attach to Area 0.",
                "Requires careful address planning to enable contiguous inter-area route summarization.",
                "Higher configuration and operational troubleshooting complexity than single-area OSPF.",
            ]
            standards_and_rfcs = [
                "RFC 2328: OSPF Version 2 (STD 54)",
            ]
            alternatives_rejected = (
                "Single-Area OSPF was rejected because multiple areas were explicitly requested; forcing a flat Area 0 would "
                "increase Dijkstra SPF calculation overhead and propagate local link flaps globally. eBGP was rejected "
                "because all nodes operate within a single Autonomous System without external boundary peering."
            )

        # Precedence 4 (Rule 3): Single AS, < 50 Subnets, Single Area -> Single-Area OSPF (Area 0)
        elif subnet_count < self.SINGLE_AREA_MAX_SUBNETS and (ospf_areas_required is None or ospf_areas_required == 1):
            rule_selected = "Rule 3: Single-Area OSPF (Area 0) Precedence"
            recommended_protocol = "Single-Area OSPF (Area 0)"
            architecture_type = "Interior Gateway Protocol (IGP) - Single-Area Link-State"
            
            multi_site_note = ""
            if site_count > 1:
                multi_site_note = (
                    f" Architectural Note on Multi-Site Topology: Although this network spans {site_count} physical sites, "
                    f"all sites belong to a single Autonomous System with no external AS boundary. Multi-site topology alone "
                    f"does NOT mandate BGP; private campus/metro transport links operating under a single administration "
                    f"are efficiently routed using internal link-state protocols (RFC 2328)."
                )

            reason_for_selection = (
                f"The network comprises a single Autonomous System with {subnet_count} subnets "
                f"(under the {self.SINGLE_AREA_MAX_SUBNETS}-subnet scalability guideline) and {site_count} site(s) "
                f"within an internal routing domain. Single-Area OSPF (RFC 2328) with all interfaces assigned to Area 0 (Backbone) "
                f"is recommended. In single-area OSPF, every router synchronizes an identical Link-State Database (LSDB) "
                f"describing all routers and interconnecting links. Each router independently executes Dijkstra's Shortest Path First (SPF) "
                f"algorithm to calculate a loop-free, shortest-path tree based on interface costs (Cost = Reference Bandwidth / Interface Bandwidth). "
                f"For topologies under {self.SINGLE_AREA_MAX_SUBNETS} subnets, single-area OSPF delivers sub-second convergence with minimal administrative overhead.{multi_site_note}"
            )
            as_info = {
                "as_count": 1,
                "is_multi_as": False,
                "has_external_boundary": False,
                "description": "Single enterprise/campus Autonomous System internal routing domain.",
            }
            ospf_info = {
                "area_count": 1,
                "backbone_area": "Area 0 (0.0.0.0)",
                "requires_area_0": True,
                "requires_abr": False,
                "area_roles": {
                    "Area 0 (0.0.0.0)": "Single flat backbone area containing all routers, links, and subnets.",
                },
                "design_notes": (
                    "All router interfaces belong to Area 0. No Area Border Routers (ABRs) or inter-area summarization "
                    "are required. All routers share an identical Link-State Database (LSDB)."
                ),
            }
            area_0_required = True
            abr_required = False
            requires_design_review = False
            routing_characteristics = [
                "Flat link-state architecture where all routers maintain identical Link-State Databases (LSDB).",
                "Link-State Advertisements (Type 1 Router LSAs, Type 2 Network LSAs) flood throughout Area 0.",
                "Each router independently executes Dijkstra's SPF algorithm to compute loop-free shortest paths.",
                "Protocol metric based on interface bandwidth (Cost = Reference Bandwidth / Bandwidth).",
            ]
            advantages = [
                "Fast convergence: link-state changes trigger immediate flooding and local SPF recalculation without counting-to-infinity.",
                "Loop-free topology guaranteed by Dijkstra's SPF shortest-path tree calculation.",
                "Minimal administrative complexity: eliminates area boundary planning, virtual links, and ABR summarization.",
            ]
            limitations = [
                "Every router maintains the entire topology graph in RAM; LSDB size scales linearly with links and routers.",
                "A link flap anywhere in the network causes all routers in Area 0 to re-run the Dijkstra SPF algorithm.",
                f"Operational heuristic: single-area design is recommended for topologies under {self.SINGLE_AREA_MAX_SUBNETS} subnets; "
                "larger topologies should evaluate multi-area partitioning.",
            ]
            standards_and_rfcs = [
                "RFC 2328: OSPF Version 2 (STD 54)",
            ]
            alternatives_rejected = (
                f"Multi-Area OSPF was rejected because the subnet scale ({subnet_count} subnets) is under the "
                f"{self.SINGLE_AREA_MAX_SUBNETS}-subnet threshold, making multi-area hierarchy unnecessary overhead. "
                "eBGP was rejected because the network operates within a single Autonomous System without external AS peering. "
                "Distance-vector protocols (such as RIPv2) were rejected due to slow hop-by-hop convergence and a 15-hop limit."
            )

        # Precedence 5 (Rule 4): Boundary Scale Review (Subnets >= 50 without explicit area count)
        elif subnet_count >= self.SINGLE_AREA_MAX_SUBNETS and ospf_areas_required is None:
            rule_selected = "Rule 4: Scale Review / Area Partitioning Requirement"
            recommended_protocol = "Design Review Required: OSPF Area Partitioning"
            architecture_type = "Hierarchical IGP Planning"
            reason_for_selection = (
                f"The network specifies {subnet_count} subnets (>= {self.SINGLE_AREA_MAX_SUBNETS} threshold) within a single "
                f"Autonomous System, but no explicit OSPF area partitioning (ospf_areas_required) was specified. "
                f"While RFC 2328 does not define a rigid mathematical limit on subnets, industry engineering guidelines "
                f"recommend partitioning networks with {self.SINGLE_AREA_MAX_SUBNETS} or more subnets into a multi-area OSPF hierarchy "
                f"to limit Dijkstra SPF recalculation frequency, contain LSA flooding domains, and reduce LSDB memory footprint. "
                f"However, the engine will not arbitrarily invent area boundary definitions without topological domain knowledge. "
                f"Recommendation: The network designer should review router CPU/memory limits and explicitly specify "
                f"ospf_areas_required (>= 2) with Area 0 as the backbone."
            )
            as_info = {
                "as_count": 1,
                "is_multi_as": False,
                "has_external_boundary": False,
                "description": "Single Autonomous System with large-scale internal subnet count requiring architectural review.",
            }
            ospf_info = {
                "area_count": None,
                "backbone_area": "Area 0 (0.0.0.0)",
                "requires_area_0": True,
                "requires_abr": True,
                "area_roles": {
                    "Area 0 (Backbone)": "Recommended central transit backbone.",
                    "Non-backbone Areas": "Recommended to partition subnets by building, site, or function.",
                },
                "design_notes": (
                    f"Subnet count ({subnet_count}) exceeds the single-area guideline ({self.SINGLE_AREA_MAX_SUBNETS}). "
                    "Explicit area partitioning is required to avoid global SPF recalculation churn."
                ),
            }
            area_0_required = True
            abr_required = True
            requires_design_review = True
            routing_characteristics = [
                f"Subnet count ({subnet_count}) reaches or exceeds the academic/operational single-area threshold ({self.SINGLE_AREA_MAX_SUBNETS}).",
                "Full-mesh LSDB synchronization across >= 50 subnets risks excessive CPU utilization during link flaps.",
                "Requires architectural partitioning into Area 0 (Backbone) plus one or more non-backbone areas.",
            ]
            advantages = [
                "Prevents accidental deployment of oversized single-area link-state flooding domains.",
                "Forces deliberate architectural planning of Area Border Router (ABR) placement and route summarization.",
            ]
            limitations = [
                "Requires input clarification from network designer on geographic or departmental area boundaries.",
            ]
            standards_and_rfcs = [
                "RFC 2328: OSPF Version 2 (STD 54)",
            ]
            alternatives_rejected = (
                f"Single-Area OSPF was not automatically selected because {subnet_count} subnets exceeds the {self.SINGLE_AREA_MAX_SUBNETS}-subnet "
                "heuristic where flat LSDB flooding introduces performance risks. Multi-Area OSPF was not automatically finalized "
                "because area partition counts cannot be guessed without topological context. eBGP was rejected because this is an internal AS domain."
            )

        # Fallback / Boundary: Subnets >= 50 with explicit ospf_areas_required == 1
        else:
            rule_selected = "Boundary: Single-Area OSPF with Scale Warning"
            recommended_protocol = "Single-Area OSPF (Area 0)"
            architecture_type = "Interior Gateway Protocol (IGP) - Single-Area Link-State"
            reason_for_selection = (
                f"The network contains {subnet_count} subnets (>= {self.SINGLE_AREA_MAX_SUBNETS} threshold) within a single "
                f"Autonomous System, and single-area OSPF was explicitly requested (ospf_areas_required: 1). "
                f"While RFC 2328 does not strictly prohibit single-area operation at this scale, deploying {subnet_count} subnets "
                f"in a single Area 0 risks frequent Dijkstra SPF recalculations across all routers whenever any link status changes. "
                f"Honoring explicit single-area request, but flagging scaling limitations for design review."
            )
            as_info = {
                "as_count": 1,
                "is_multi_as": False,
                "has_external_boundary": False,
                "description": "Single enterprise/campus Autonomous System internal routing domain.",
            }
            ospf_info = {
                "area_count": 1,
                "backbone_area": "Area 0 (0.0.0.0)",
                "requires_area_0": True,
                "requires_abr": False,
                "area_roles": {
                    "Area 0 (0.0.0.0)": "Single flat backbone area containing all routers, links, and subnets.",
                },
                "design_notes": (
                    f"Warning: Operating {subnet_count} subnets in a single area exceeds the {self.SINGLE_AREA_MAX_SUBNETS}-subnet "
                    "heuristic. Monitor router CPU and link flap metrics."
                ),
            }
            area_0_required = True
            abr_required = False
            requires_design_review = False
            routing_characteristics = [
                "Flat link-state architecture where all routers maintain identical Link-State Databases (LSDB).",
                f"Subnet scale ({subnet_count}) exceeds standard single-area recommendations.",
                "Dijkstra SPF calculations run globally upon every link flap.",
            ]
            advantages = [
                "Simpler configuration with no ABR hierarchy required.",
            ]
            limitations = [
                f"High link-state churn risk: {subnet_count} subnets in Area 0 may cause high CPU utilization during topology flaps.",
                "Lack of inter-area summarization results in larger routing tables on all routers.",
            ]
            standards_and_rfcs = [
                "RFC 2328: OSPF Version 2 (STD 54)",
            ]
            alternatives_rejected = (
                "Multi-Area OSPF was bypassed due to explicit request for single area (ospf_areas_required: 1). "
                "eBGP was rejected as all subnets belong to a single Autonomous System."
            )

        # --- 3. Academic Explainability Engine Integration ---
        audit_reasoning = (
            f"1. Evaluated Topology Conditions: network='{clean_network_name}', AS_count={autonomous_system_count}, "
            f"subnets={subnet_count}, sites={site_count}, external_boundary={has_external_as_boundary}, "
            f"ospf_areas_required={ospf_areas_required}.\n"
            f"2. Decision Rule Selected: {rule_selected}.\n"
            f"3. Recommendation: {recommended_protocol} ({architecture_type}).\n"
            f"4. Technical Justification: {reason_for_selection}\n"
            f"5. Alternative Protocol Analysis: {alternatives_rejected}\n"
            f"6. Standards Attribution: RFC 2328 (OSPFv2) governs link-state synchronization, Dijkstra SPF, Area 0, and ABR mechanics. "
            f"RFC 4271 (BGP-4) governs inter-AS path-vector exchange and AS_PATH loop prevention. "
            f"Note: The '{self.SINGLE_AREA_MAX_SUBNETS}-subnet' threshold is an engineering design heuristic for SPF scalability, not a hard RFC 2328 protocol limit."
        )

        explanation_record = self.explainability_engine.record_explanation(
            engine_name="RoutingEngine",
            input_conditions={
                "network_name": clean_network_name,
                "autonomous_system_count": autonomous_system_count,
                "subnet_count": subnet_count,
                "site_count": site_count,
                "has_external_as_boundary": has_external_as_boundary,
                "ospf_areas_required": ospf_areas_required,
                "topology_description": topology_description,
            },
            selected_recommendation={
                "recommended_protocol": recommended_protocol,
                "architecture_type": architecture_type,
                "area_0_required": area_0_required,
                "abr_required": abr_required,
                "requires_design_review": requires_design_review,
                "rule_selected": rule_selected,
            },
            technical_reasoning=audit_reasoning,
            standards_and_rfcs=standards_and_rfcs,
        )

        return {
            "network_name": clean_network_name,
            "recommended_protocol": recommended_protocol,
            "architecture_type": architecture_type,
            "reason_for_selection": reason_for_selection,
            "autonomous_system_info": as_info,
            "ospf_area_info": ospf_info,
            "area_0_required": area_0_required,
            "abr_required": abr_required,
            "routing_characteristics": routing_characteristics,
            "advantages": advantages,
            "limitations": limitations,
            "standards_and_rfcs": standards_and_rfcs,
            "explainability_record_id": explanation_record.record_id,
            "requires_design_review": requires_design_review,
        }

    # Alias for compatibility
    def recommend_routing_protocol(self, *args, **kwargs) -> Dict[str, Any]:
        """Alias for recommend_routing."""
        return self.recommend_routing(*args, **kwargs)
