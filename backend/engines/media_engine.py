"""Physical Media Recommendation Engine.

Academic Context:
Selects optimal Layer 1 physical transmission media (Twisted Pair Copper,
Multimode Optical Fiber, or Single-mode Optical Fiber) based on link distance,
throughput, signal attenuation, modal/chromatic dispersion, and user-specified constraints.

Preferred-Medium Policy Matrix:
---------------------------------------------------------------------------------------------------------
Tier / Distance Range       | Copper Preference       | Multimode (OM4) Preference | Single-mode (OS2) Preference
---------------------------------------------------------------------------------------------------------
1. Distance <= 100m         | Cat6a Copper (Default)  | OM4 MMF (Honored)          | OS2 SMF (Honored)
2. 100m < Distance <= 400m  | VIOLATION (Error 400)   | OM4 MMF (Default)          | OS2 SMF (Honored)
3. 400m < Distance <= 10km  | VIOLATION (Error 400)   | VIOLATION (Error 400)      | OS2 SMF 10GBASE-LR (Default)
4. 10km < Distance <= 40km  | VIOLATION (Error 400)   | VIOLATION (Error 400)      | OS2 SMF 10GBASE-ER (Default)
5. Distance > 40km          | VIOLATION (Error 400)   | VIOLATION (Error 400)      | VIOLATION (Error 400, > 40km)
---------------------------------------------------------------------------------------------------------

Standards & References:
- IEEE 802.3an: 10GBASE-T (10 Gbps over Cat6a balanced twisted-pair cabling up to 100m)
- IEEE 802.3ae Clause 52: 10GBASE-SR (850 nm VCSEL over OM4 multimode fiber up to 400m)
- IEEE 802.3ae Clause 52: 10GBASE-LR (1310 nm DFB laser over OS2 single-mode fiber up to 10 km)
- IEEE 802.3ae Clause 52: 10GBASE-ER (1550 nm cooled DFB/EML laser over OS2 single-mode fiber up to 40 km)
- ANSI/TIA-568-C.2: Balanced Twisted-Pair Telecommunications Cabling Standards (49.3 dB max channel loss at 500 MHz)
- TIA-492AAAD: Detail Specification for 850-nm Laser-Optimized, 50-µm Core Diameter OM4 MMF (4700 MHz·km EMB)
- ITU-T G.652.D: Characteristics of a Single-Mode Optical Fibre Cable
"""

from typing import Dict, Any, Optional, List
from engines.explainability_engine import ExplainabilityEngine


class PhysicalDistanceViolationError(ValueError):
    """Raised when a requested physical transmission medium cannot physically support the required distance."""

    def __init__(
        self,
        message: str,
        requested_medium: str = "copper",
        distance_meters: float = 0.0,
        max_distance_meters: float = 100.0,
        attenuation_explanation: str = "",
    ):
        super().__init__(message)
        self.message = message
        self.requested_medium = requested_medium
        self.distance_meters = distance_meters
        self.max_distance_meters = max_distance_meters
        self.attenuation_explanation = attenuation_explanation


class MediaEngine:
    """Engine responsible for physical layer transmission media recommendations."""

    # Standard-defined 10GBASE-LR specifications (IEEE 802.3ae Clause 52)
    LR_TX_POWER_MIN_DBM: float = -8.2          # Minimum transmitter launch power
    LR_RX_SENSITIVITY_DBM: float = -14.4       # Minimum receiver sensitivity
    LR_OPTICAL_BUDGET_DB: float = 6.2          # Available optical power budget (TX_min - RX_sensitivity)
    LR_FIBER_ATTENUATION_DB_PER_KM: float = 0.4  # Attenuation coefficient at 1310 nm for OS2 (conservative engineering value)
    LR_MAX_DISTANCE_METERS: float = 10000.0    # 10 km reach limit for 10GBASE-LR

    # Standard-defined 10GBASE-ER specifications (IEEE 802.3ae Clause 52)
    ER_TX_POWER_MIN_DBM: float = -4.7          # Minimum transmitter launch power for 10GBASE-ER
    ER_RX_SENSITIVITY_DBM: float = -15.8       # Minimum receiver sensitivity for 10GBASE-ER
    ER_OPTICAL_BUDGET_DB: float = 11.1         # Available optical power budget (TX_min - RX_sensitivity)
    ER_FIBER_ATTENUATION_DB_PER_KM: float = 0.25  # Attenuation coefficient at 1550 nm for OS2
    ER_MAX_DISTANCE_METERS: float = 40000.0    # 40 km reach limit for 10GBASE-ER

    # Engineering assumptions and installation estimates
    CONNECTOR_LOSS_DB: float = 1.0             # Estimated insertion loss for 2x mated LC connector pairs (0.5 dB/pair per TIA-568-C.3)
    SAFETY_MARGIN_DB: float = 3.0              # Engineering safety margin for component aging, temperature drift, and maintenance splices

    def __init__(self, explainability_engine: Optional[ExplainabilityEngine] = None):
        self.explainability_engine = explainability_engine or ExplainabilityEngine()
        self.is_ready = True

    def _normalize_preferred_medium(self, preferred_medium: Optional[str]) -> Optional[str]:
        """Normalizes and validates preferred medium strings."""
        if not preferred_medium:
            return None
        val = preferred_medium.strip().lower()
        if val in {"copper", "cat6a", "twisted_pair", "copper_cat6a"}:
            return "copper"
        elif val in {"multimode_fiber", "om4", "mmf", "fiber_multimode"}:
            return "multimode_fiber"
        elif val in {"singlemode_fiber", "os2", "smf", "fiber_singlemode"}:
            return "singlemode_fiber"
        elif val in {"fiber"}:
            return "fiber"
        else:
            raise ValueError(
                f"Invalid preferred_medium '{preferred_medium}'. Supported options are: 'copper', 'multimode_fiber', 'singlemode_fiber', 'fiber'."
            )

    def _calculate_optical_budget(
        self,
        distance_meters: float,
        optic_type: str = "10GBASE-LR",
    ) -> Dict[str, Any]:
        """Calculates optical link power budget, distinguishing standard transceiver limits from installation estimates.

        Calculates:
        - Fiber loss = attenuation_coefficient * distance_km
        - Total estimated loss = fiber_loss + connector_loss + safety_margin
        - Power margin = available_budget - total_estimated_loss
        - is_budget_sufficient: True if total_estimated_loss <= available_budget, False otherwise.
        """
        distance_km = distance_meters / 1000.0

        if optic_type == "10GBASE-ER":
            tx_min = self.ER_TX_POWER_MIN_DBM
            rx_sens = self.ER_RX_SENSITIVITY_DBM
            budget = self.ER_OPTICAL_BUDGET_DB
            alpha = self.ER_FIBER_ATTENUATION_DB_PER_KM
            std_reach_km = 40.0
        else:
            tx_min = self.LR_TX_POWER_MIN_DBM
            rx_sens = self.LR_RX_SENSITIVITY_DBM
            budget = self.LR_OPTICAL_BUDGET_DB
            alpha = self.LR_FIBER_ATTENUATION_DB_PER_KM
            std_reach_km = 10.0

        fiber_loss = round(alpha * distance_km, 3)
        conn_loss = self.CONNECTOR_LOSS_DB
        safety = self.SAFETY_MARGIN_DB
        total_loss = round(fiber_loss + conn_loss + safety, 3)
        power_margin = round(budget - total_loss, 3)
        is_sufficient = total_loss <= budget

        if is_sufficient:
            budget_status = "sufficient"
            engineering_rec = (
                f"Optical power budget is sufficient: Estimated channel loss ({total_loss:.2f} dB) "
                f"operates within the {budget:.1f} dB budget with a +{power_margin:.2f} dB surplus margin."
            )
        else:
            budget_status = "insufficient_under_conservative_assumptions"
            deficit = round(abs(power_margin), 3)
            if optic_type == "10GBASE-LR":
                engineering_rec = (
                    f"Standardized reach (10 km) is IEEE 802.3ae compliant, but modeled installation assumptions "
                    f"({alpha} dB/km fiber + {conn_loss:.1f} dB connector + {safety:.1f} dB safety margin = {total_loss:.2f} dB) "
                    f"exceed the standard 6.2 dB transceiver budget by {deficit:.2f} dB. "
                    f"Additional link engineering required: (1) Deploy continuous fusion splices (< 0.1 dB loss) instead "
                    f"of patch connectors; (2) Verify actual installed fiber attenuation (typical ITU-T G.652.D is 0.32-0.35 dB/km); "
                    f"(3) Reduce the design safety margin buffer from 3.0 dB to 1.0-1.5 dB for stable indoor/campus environments; "
                    f"or (4) Upgrade to 10GBASE-ER optics (11.1 dB budget) for guaranteed link margin."
                )
            else:
                engineering_rec = (
                    f"Standardized reach (40 km) is IEEE 802.3ae compliant, but modeled installation assumptions "
                    f"({alpha} dB/km fiber + {conn_loss:.1f} dB connector + {safety:.1f} dB safety margin = {total_loss:.2f} dB) "
                    f"exceed the standard 11.1 dB transceiver budget by {deficit:.2f} dB. "
                    f"Additional link engineering required: (1) Specify premium low-loss optical fiber (<= 0.20 dB/km at 1550 nm); "
                    f"(2) Eliminate patch panels along the span via direct fusion splicing; "
                    f"(3) Calibrate safety margin using OTDR field measurements; or "
                    f"(4) Deploy 10GBASE-ZR optics (80 km reach, 24 dB budget) or active EDFA optical pre-amplifiers."
                )

        return {
            "tx_power_min_dbm": tx_min,
            "rx_sensitivity_dbm": rx_sens,
            "power_budget_db": budget,
            "attenuation_coefficient_db_per_km": alpha,
            "fiber_loss_db": fiber_loss,
            "connector_loss_db": conn_loss,
            "safety_margin_db": safety,
            "total_estimated_loss_db": total_loss,
            "power_margin_db": power_margin,
            "is_budget_sufficient": is_sufficient,
            "budget_status": budget_status,
            "engineering_recommendation": engineering_rec,
        }

    def recommend_media(
        self,
        distance_meters: float,
        preferred_medium: Optional[str] = None,
        required_bandwidth_mbps: float = 10000.0,
        environment: str = "indoor",
        budget_priority: str = "balanced",
    ) -> Dict[str, Any]:
        """Calculates the optimal physical transmission medium based on link distance and user constraints.

        Args:
            distance_meters: Physical length of the network segment (must be > 0).
            preferred_medium: Optional preferred medium constraint ('copper', 'multimode_fiber', 'singlemode_fiber', 'fiber').
            required_bandwidth_mbps: Target link throughput in Mbps (default: 10000 / 10 Gbps).
            environment: Environmental conditions ('indoor', 'industrial', 'outdoor').
            budget_priority: Cost preference ('low_cost', 'balanced', 'performance').

        Returns:
            Dict containing full recommendation specification, technical justification,
            standards references, alternative analysis, and explainability tracking.

        Raises:
            ValueError: If distance_meters <= 0 or preferred_medium is invalid.
            PhysicalDistanceViolationError: If an explicitly requested medium violates distance/attenuation limits,
                                            or if distance exceeds unamplified Ethernet optical reach (40 km).
        """
        # 1. Input Validation
        if distance_meters is None or distance_meters <= 0:
            raise ValueError(
                f"Distance must be positive and greater than 0 metres. Received: {distance_meters}"
            )

        norm_preferred = self._normalize_preferred_medium(preferred_medium)

        # 2. Maximum Unamplified Ethernet Reach Check (> 40 km)
        if distance_meters > self.ER_MAX_DISTANCE_METERS:
            raise PhysicalDistanceViolationError(
                message=(
                    f"Physical distance violation: Link distance of {distance_meters}m exceeds the maximum 40 km reach "
                    f"of standard unamplified 10 Gigabit Ethernet (10GBASE-ER, IEEE 802.3ae). Point-to-point links "
                    f"exceeding 40 km require active optical line amplifiers (EDFA), DWDM transponders, or carrier WAN services."
                ),
                requested_medium=preferred_medium or "any",
                distance_meters=distance_meters,
                max_distance_meters=self.ER_MAX_DISTANCE_METERS,
                attenuation_explanation=(
                    f"Standard unamplified 10GBASE-ER optics at 1550 nm provide an 11.1 dB optical power budget, "
                    f"limiting single-span reach to 40,000 metres. Beyond 40 km, fiber attenuation and chromatic dispersion "
                    f"require active erbium-doped fiber amplifiers (EDFA) and dispersion compensation modules (DCM)."
                ),
            )

        # 3. Explicit Constraint Incompatibility Checks
        if norm_preferred == "copper" and distance_meters > 100.0:
            attenuation_msg = (
                "Twisted-pair copper cabling (Cat6a) is governed by IEEE 802.3an and ANSI/TIA-568-C.2, "
                "which strictly enforce a maximum 100-meter channel length (90m horizontal + 10m patch cords). "
                "At 500 MHz, the maximum allowable channel insertion loss specified by ANSI/TIA-568-C.2 is 49.3 dB. "
                "Beyond 100 metres, electrical attenuation, skin effect, and inter-symbol interference (ISI) cause excessive "
                "signal degradation, dropping the signal-to-noise ratio (SNR) below the receiver threshold and causing total "
                "link failure. Optical transmission media must be utilized."
            )
            raise PhysicalDistanceViolationError(
                message=(
                    f"Physical distance violation: Requested copper medium cannot support a link distance "
                    f"of {distance_meters}m. Maximum permissible reach for Cat6a 10GBASE-T is 100 metres."
                ),
                requested_medium=preferred_medium or "copper",
                distance_meters=distance_meters,
                max_distance_meters=100.0,
                attenuation_explanation=attenuation_msg,
            )

        if norm_preferred == "multimode_fiber" and distance_meters > 400.0:
            attenuation_msg = (
                "OM4 laser-optimized multimode fiber operating at 850 nm (10GBASE-SR) is strictly limited "
                "to a maximum reach of 400 metres under IEEE 802.3ae and TIA-492AAAD. Beyond 400 metres, modal dispersion "
                "(differential mode delay) causes severe optical pulse spreading and inter-symbol interference, "
                "exceeding the allowable receiver dispersion penalty. Single-mode optical fiber (OS2) is required."
            )
            raise PhysicalDistanceViolationError(
                message=(
                    f"Physical distance violation: Requested multimode fiber medium cannot support a link distance "
                    f"of {distance_meters}m. Maximum reach for OM4 10GBASE-SR at 850 nm is 400 metres."
                ),
                requested_medium=preferred_medium or "multimode_fiber",
                distance_meters=distance_meters,
                max_distance_meters=400.0,
                attenuation_explanation=attenuation_msg,
            )

        # 4. Media Selection & Preferred-Medium Handling
        optical_budget_data: Optional[Dict[str, Any]] = None

        honor_mmf_at_short_range = (distance_meters <= 100.0 and norm_preferred == "multimode_fiber")
        honor_smf_at_short_range = (distance_meters <= 400.0 and norm_preferred == "singlemode_fiber")

        if honor_smf_at_short_range or (distance_meters > 400.0 and distance_meters <= self.LR_MAX_DISTANCE_METERS):
            # OS2 10GBASE-LR Tier: Either explicitly requested for <= 400m, or default for 400m < distance <= 10km
            selected_medium = "OS2 Single-Mode Optical Fiber (9/125 µm)"
            technology_standard = "10GBASE-LR (IEEE 802.3ae Clause 52)"
            wavelength_nm = 1310
            max_supported_distance_meters = self.LR_MAX_DISTANCE_METERS
            maximum_bandwidth_mbps = 10000.0
            attenuation_rating = "Ultra-low optical attenuation (~0.4 dB/km at 1310 nm per ITU-T G.652.D)"
            cost_index = "High (single-mode laser diode transceivers and sub-micron core alignment)"

            optical_budget_data = self._calculate_optical_budget(distance_meters, "10GBASE-LR")

            pref_note = ""
            if honor_smf_at_short_range:
                pref_note = (
                    f"Note: Explicit preference for single-mode fiber honored for {distance_meters}m link. "
                    f"While copper (<=100m) or OM4 (101-400m) is the default cost-effective medium, OS2 eliminates "
                    f"modal dispersion and offers future-proof expansion for high-speed campus backbones.\n\n"
                )

            # Distinguish standard reach, estimated loss, and budget sufficiency
            if optical_budget_data["is_budget_sufficient"]:
                sufficiency_note = (
                    f"- Budget Status: SUFFICIENT (+{optical_budget_data['power_margin_db']:.2f} dB surplus margin).\n"
                )
            else:
                sufficiency_note = (
                    f"- Budget Status: INSUFFICIENT under chosen conservative installation assumptions "
                    f"(Deficit: {abs(optical_budget_data['power_margin_db']):.2f} dB).\n"
                    f"  Distinction: Standardized transceiver reach (10 km) is fully IEEE 802.3ae compliant, but the "
                    f"modeled installation assumptions (1.0 dB connector loss + 3.0 dB safety margin) exceed the available "
                    f"6.2 dB budget. Link engineering required: deploy low-loss fusion splices, verify actual field fiber "
                    f"attenuation (< 0.35 dB/km), adjust safety margins, or select 10GBASE-ER optics.\n"
                )

            technical_reasoning = (
                f"{pref_note}"
                f"OS2 single-mode optical fiber (9/125 µm core) operating at 1310 nm with 10GBASE-LR optical transceivers "
                f"(IEEE 802.3ae Clause 52) supports link distances up to 10 km ({distance_meters}m evaluated). "
                f"Because the 9 µm core diameter permits only a single fundamental transverse mode to propagate, modal dispersion "
                f"is fundamentally eliminated, leaving chromatic dispersion as the only propagation impairment. With a conservative "
                f"attenuation coefficient of ~0.4 dB/km at 1310 nm, OS2 reliably supports spans up to 10,000 metres.\n\n"
                f"Optical Power Budget Analysis (Standard Specifications vs. Installation Estimates):\n"
                f"- Standard Transceiver Budget (IEEE 802.3ae): {self.LR_OPTICAL_BUDGET_DB:.1f} dB "
                f"(Transmitter Min: {self.LR_TX_POWER_MIN_DBM:.1f} dBm, Receiver Sensitivity: {self.LR_RX_SENSITIVITY_DBM:.1f} dBm)\n"
                f"- Standardized Maximum Transceiver Reach: 10,000 m (10 km)\n"
                f"- Fiber Attenuation Loss (Estimated @ 0.4 dB/km): {optical_budget_data['fiber_loss_db']:.3f} dB\n"
                f"- Connector Insertion Loss (Estimated 2 pairs @ 0.5 dB): {self.CONNECTOR_LOSS_DB:.1f} dB\n"
                f"- Engineering Safety/Aging Margin (Design Assumption): {self.SAFETY_MARGIN_DB:.1f} dB\n"
                f"- Total Estimated Channel Loss: {optical_budget_data['total_estimated_loss_db']:.3f} dB\n"
                f"- Net Unallocated Power Margin: {optical_budget_data['power_margin_db']:.3f} dB\n"
                f"{sufficiency_note}"
            )

            why_alternatives_not_selected = {
                "Cat6a Balanced Twisted Pair Copper": (
                    "Exceeds the 100-meter physical channel limit for 10GBASE-T. Beyond 100m, electrical attenuation "
                    "and skin effect cause total signal degradation."
                ),
                "OM4 Multimode Fiber": (
                    "Exceeds the 400-meter modal dispersion limit for 10GBASE-SR at 850 nm. Beyond 400m, differential "
                    "mode delay (DMD) causes severe optical pulse spreading and unacceptable bit error rates."
                    if distance_meters > 400.0 else
                    "User explicitly requested single-mode fiber; OM4 was bypassed in favor of requested infrastructure."
                ),
            }

            assumptions_and_limitations = [
                f"Standardized maximum transceiver reach is 10,000 metres (10 km) under IEEE 802.3ae Clause 52.",
                f"Estimated total link loss is {optical_budget_data['total_estimated_loss_db']:.2f} dB based on 0.4 dB/km fiber loss, 1.0 dB connector loss, and a 3.0 dB safety margin.",
                (
                    f"Optical link budget is sufficient (+{optical_budget_data['power_margin_db']:.2f} dB margin)."
                    if optical_budget_data["is_budget_sufficient"]
                    else f"Optical budget deficit: {-optical_budget_data['power_margin_db']:.2f} dB under chosen conservative installation assumptions. Link engineering optimization required for 10 km span."
                ),
                "Requires compliance with minimum bend-radius specifications (ITU-T G.652.D).",
            ]

            standards_and_rfcs = [
                "IEEE 802.3ae Clause 52 (10GBASE-LR 1310 nm Long-Reach Optical Interface)",
                "ITU-T G.652.D (Characteristics of a Single-Mode Optical Fibre Cable)",
                "ANSI/TIA-568-C.3 (Optical Fiber Cabling Components Standard)",
            ]

        elif distance_meters > self.LR_MAX_DISTANCE_METERS and distance_meters <= self.ER_MAX_DISTANCE_METERS:
            # OS2 10GBASE-ER Tier: 10,001m to 40,000m (40 km reach)
            selected_medium = "OS2 Single-Mode Optical Fiber (9/125 µm) - Extended Reach"
            technology_standard = "10GBASE-ER (IEEE 802.3ae Clause 52)"
            wavelength_nm = 1550
            max_supported_distance_meters = self.ER_MAX_DISTANCE_METERS
            maximum_bandwidth_mbps = 10000.0
            attenuation_rating = "Ultra-low optical attenuation (~0.25 dB/km at 1550 nm per ITU-T G.652.D)"
            cost_index = "Very High (cooled 1550 nm DFB/EML laser diodes and high-sensitivity APD/PIN receivers)"

            optical_budget_data = self._calculate_optical_budget(distance_meters, "10GBASE-ER")

            if optical_budget_data["is_budget_sufficient"]:
                sufficiency_note = (
                    f"- Budget Status: SUFFICIENT (+{optical_budget_data['power_margin_db']:.2f} dB surplus margin).\n"
                )
            else:
                sufficiency_note = (
                    f"- Budget Status: INSUFFICIENT under chosen conservative installation assumptions "
                    f"(Deficit: {abs(optical_budget_data['power_margin_db']):.2f} dB).\n"
                    f"  Distinction: Standardized transceiver reach (40 km) is IEEE 802.3ae compliant (10.9 dB maximum channel loss), "
                    f"but modeled installation assumptions (10.0 dB fiber + 1.0 dB connector + 3.0 dB safety margin = 14.0 dB) "
                    f"exceed the standard 11.1 dB budget. Link engineering required: specify low-loss fiber (<= 0.20 dB/km), "
                    f"eliminate patch connectors via fusion splicing, or deploy active optical amplification.\n"
                )

            technical_reasoning = (
                f"Link distance of {distance_meters}m exceeds the 10,000-meter (10 km) reach limit of standard 10GBASE-LR optics. "
                f"Therefore, 10GBASE-ER extended-reach single-mode optical transceivers (IEEE 802.3ae Clause 52) operating at "
                f"1550 nm over OS2 single-mode optical fiber are required. Operating in the 1550 nm low-loss optical window "
                f"reduces fiber attenuation to ~0.25 dB/km (compared to ~0.4 dB/km at 1310 nm). Coupled with higher-power cooled "
                f"DFB/EML laser transmitters (minimum launch power: -4.7 dBm) and sensitive receivers (-15.8 dBm sensitivity), "
                f"10GBASE-ER yields an 11.1 dB optical budget supporting unamplified link distances up to 40,000 metres (40 km).\n\n"
                f"Optical Power Budget Analysis (Standard Specifications vs. Installation Estimates):\n"
                f"- Standard Transceiver Budget (IEEE 802.3ae): {self.ER_OPTICAL_BUDGET_DB:.1f} dB "
                f"(Transmitter Min: {self.ER_TX_POWER_MIN_DBM:.1f} dBm, Receiver Sensitivity: {self.ER_RX_SENSITIVITY_DBM:.1f} dBm)\n"
                f"- Standardized Maximum Transceiver Reach: 40,000 m (40 km)\n"
                f"- Fiber Attenuation Loss (Estimated @ 0.25 dB/km): {optical_budget_data['fiber_loss_db']:.3f} dB\n"
                f"- Connector Insertion Loss (Estimated 2 pairs @ 0.5 dB): {self.CONNECTOR_LOSS_DB:.1f} dB\n"
                f"- Engineering Safety/Aging Margin (Design Assumption): {self.SAFETY_MARGIN_DB:.1f} dB\n"
                f"- Total Estimated Channel Loss: {optical_budget_data['total_estimated_loss_db']:.3f} dB\n"
                f"- Net Unallocated Power Margin: {optical_budget_data['power_margin_db']:.3f} dB\n"
                f"{sufficiency_note}"
            )

            why_alternatives_not_selected = {
                "10GBASE-LR (1310 nm Single-mode)": (
                    f"Exceeds the 10,000-meter (10 km) specified reach of 10GBASE-LR under IEEE 802.3ae. "
                    f"At {distance_meters}m, optical attenuation and dispersion exceed the 6.2 dB budget of 10GBASE-LR."
                ),
                "Cat6a Balanced Twisted Pair Copper": (
                    "Exceeds 100m channel limit; completely unviable for metropolitan link distances."
                ),
                "OM4 Multimode Fiber": (
                    "Exceeds 400m modal dispersion limit for 10GBASE-SR; unviable."
                ),
            }

            assumptions_and_limitations = [
                "Standardized maximum transceiver reach is 40,000 metres (40 km) under IEEE 802.3ae Clause 52.",
                f"Estimated total link loss is {optical_budget_data['total_estimated_loss_db']:.2f} dB based on 0.25 dB/km fiber loss, 1.0 dB connector loss, and a 3.0 dB safety margin.",
                (
                    f"Optical link budget is sufficient (+{optical_budget_data['power_margin_db']:.2f} dB margin)."
                    if optical_budget_data["is_budget_sufficient"]
                    else f"Optical budget deficit: {-optical_budget_data['power_margin_db']:.2f} dB under chosen conservative installation assumptions. Link engineering optimization required for 40 km span."
                ),
                "Unamplified link reach strictly bounded at 40,000 metres; spans > 40 km require optical line amplification (EDFA).",
            ]

            standards_and_rfcs = [
                "IEEE 802.3ae Clause 52 (10GBASE-ER 1550 nm Extended-Reach Optical Interface)",
                "ITU-T G.652.D (Characteristics of a Single-Mode Optical Fibre Cable)",
                "ANSI/TIA-568-C.3 (Optical Fiber Cabling Components Standard)",
            ]

        elif honor_mmf_at_short_range or (distance_meters > 100.0 and distance_meters <= 400.0):
            # OM4 Multimode Fiber Tier
            selected_medium = "OM4 Laser-Optimized Multimode Fiber (50/125 µm)"
            technology_standard = "10GBASE-SR (IEEE 802.3ae Clause 52)"
            wavelength_nm = 850
            max_supported_distance_meters = 400.0
            maximum_bandwidth_mbps = 10000.0
            attenuation_rating = "Low optical attenuation (~3.0 dB/km at 850 nm per TIA-492AAAD)"
            cost_index = "Moderate (economical 850 nm VCSEL lasers and LC duplex transceivers)"

            pref_note = ""
            if honor_mmf_at_short_range:
                pref_note = (
                    f"Note: Explicit preference for multimode fiber honored for {distance_meters}m link. "
                    f"While Cat6a copper is the default for <= 100m due to integrated RJ-45 PHY interfaces, "
                    f"OM4 multimode fiber provides total immunity to electromagnetic interference (EMI) and electrical isolation.\n\n"
                )

            technical_reasoning = (
                f"{pref_note}"
                f"OM4 laser-optimized multimode fiber (50/125 µm core) operating at an 850 nm wavelength with "
                f"10GBASE-SR short-reach optical transceivers (IEEE 802.3ae Clause 52) is selected for link distances between "
                f"101 and 400 metres ({distance_meters}m evaluated). OM4 provides a standard-specified Effective Modal "
                f"Bandwidth (EMB) of 4700 MHz·km at 850 nm per TIA-492AAAD when driven by Vertical-Cavity Surface-Emitting "
                f"Lasers (VCSELs). This high modal bandwidth minimizes Differential Mode Delay (DMD), mitigating modal dispersion "
                f"and preventing inter-symbol interference across the 400-meter reach, while utilizing lower-cost 850 nm VCSEL "
                f"optics with wider alignment tolerances than single-mode laser diodes."
            )

            why_alternatives_not_selected = {
                "Cat6a Balanced Twisted Pair Copper": (
                    "Exceeds the 100-meter maximum channel length defined by IEEE 802.3an and ANSI/TIA-568-C.2. "
                    "Beyond 100m, copper experiences severe insertion loss and high-frequency attenuation that prevents link establishment."
                    if distance_meters > 100.0 else
                    "User explicitly requested multimode fiber; Cat6a copper was bypassed to fulfill the specified medium preference."
                ),
                "OS2 Single-mode Fiber": (
                    "While OS2 single-mode fiber can span this distance, single-mode laser transceivers (1310 nm DFB) require "
                    "tight sub-micron alignment to 9 µm cores and optical isolators. OM4 achieves full 10 Gbps throughput "
                    "up to 400m with more economical 850 nm VCSEL transceivers."
                ),
            }

            assumptions_and_limitations = [
                "Requires 850 nm VCSEL-based 10GBASE-SR optical transceivers with LC duplex connectors.",
                "Total channel reach is strictly limited to 400 metres at 10 Gbps; cannot be extended beyond 400m due to modal dispersion.",
                "Ideal for campus building-to-building risers and data center spine-leaf interconnects within 400m.",
            ]

            standards_and_rfcs = [
                "IEEE 802.3ae Clause 52 (10GBASE-SR 850 nm Short-Reach Optical Interface)",
                "TIA-492AAAD (Detail Specification for 850-nm Laser-Optimized, 50-µm Core Diameter OM4 MMF)",
                "ISO/IEC 11801 Type OM4 Optical Fiber Specification",
            ]

        else:
            # Distance <= 100m and preferred medium is copper (or None/default)
            selected_medium = "Cat6a Balanced Twisted Pair Copper"
            technology_standard = "10GBASE-T (IEEE 802.3an)"
            wavelength_nm = None
            max_supported_distance_meters = 100.0
            maximum_bandwidth_mbps = 10000.0
            attenuation_rating = "Standard insertion loss <= 49.3 dB at 500 MHz over 100m channel (ANSI/TIA-568-C.2)"
            cost_index = "Low (standard switch-integrated RJ-45 PHY interfaces, no pluggable optical transceivers required)"

            technical_reasoning = (
                f"Category 6A (Cat6a) balanced twisted-pair copper cable is recommended for link distances <= 100 metres "
                f"({distance_meters}m requested) under the IEEE 802.3an 10GBASE-T and ANSI/TIA-568-C.2 standards. "
                f"Cat6a operates at frequencies up to 500 MHz and incorporates alien crosstalk (ANEXT) suppression "
                f"to reliably achieve 10 Gbps throughput across the full 100-meter channel (90m horizontal solid-conductor + "
                f"10m stranded patch cords). Per ANSI/TIA-568-C.2, the maximum channel insertion loss at 500 MHz is 49.3 dB. "
                f"Cat6a provides the most cost-effective solution through switch-integrated RJ-45 modular interfaces, "
                f"backward compatibility with 1000BASE-T/100BASE-TX, and zero requirement for pluggable optical transceivers."
            )

            why_alternatives_not_selected = {
                "OM4 Multimode Fiber": (
                    "OM4 fiber supports 10GBASE-SR up to 400m, but requires pluggable optical transceivers (SFP+ 850 nm) "
                    "and optical patch terminations, introducing additional hardware components without functional distance "
                    "benefit within 100 metres."
                ),
                "OS2 Single-mode Fiber": (
                    "OS2 fiber requires precision 1310 nm laser transceivers (10GBASE-LR) and sub-micron alignment. "
                    "Using single-mode fiber over <= 100m adds transceiver expense and may require optical attenuation to "
                    "prevent photodetector receiver saturation over short patch distances."
                ),
            }

            assumptions_and_limitations = [
                "Channel length must not exceed 100 metres total (90 metres permanent link + 10 metres combined patch cords per ANSI/TIA-568-C.2).",
                "Compliance with ANSI/TIA-568-C.2 Category 6A specifications and proper RJ-45 termination is required to prevent alien crosstalk.",
                "Suitable for horizontal intra-floor enterprise distribution and server-to-switch patch connections.",
            ]

            standards_and_rfcs = [
                "IEEE 802.3an (10GBASE-T Physical Layer Specifications)",
                "ANSI/TIA-568-C.2 (Balanced Twisted-Pair Telecommunications Cabling)",
                "ISO/IEC 11801 Class EA Channel Specifications",
            ]

        # 5. Explainability Engine Integration
        explanation_record = self.explainability_engine.record_explanation(
            engine_name="MediaEngine",
            input_conditions={
                "distance_meters": distance_meters,
                "preferred_medium": preferred_medium,
                "required_bandwidth_mbps": required_bandwidth_mbps,
                "environment": environment,
                "budget_priority": budget_priority,
            },
            selected_recommendation={
                "selected_medium": selected_medium,
                "technology_standard": technology_standard,
                "wavelength_nm": wavelength_nm,
                "max_supported_distance_meters": max_supported_distance_meters,
                "maximum_bandwidth_mbps": maximum_bandwidth_mbps,
            },
            technical_reasoning=technical_reasoning,
            standards_and_rfcs=standards_and_rfcs,
        )

        return {
            "input_distance_meters": distance_meters,
            "requested_medium": preferred_medium,
            "selected_medium": selected_medium,
            "technology_standard": technology_standard,
            "wavelength_nm": wavelength_nm,
            "max_supported_distance_meters": max_supported_distance_meters,
            "maximum_bandwidth_mbps": maximum_bandwidth_mbps,
            "attenuation_rating": attenuation_rating,
            "cost_index": cost_index,
            "technical_reasoning": technical_reasoning,
            "why_alternatives_not_selected": why_alternatives_not_selected,
            "assumptions_and_limitations": assumptions_and_limitations,
            "standards_and_rfcs": standards_and_rfcs,
            "optical_budget": optical_budget_data,
            "explanation_record_id": explanation_record.record_id,
            # Backward compatibility fields
            "recommended_media": selected_medium,
            "cable_standard": technology_standard,
            "rationale": technical_reasoning,
        }
