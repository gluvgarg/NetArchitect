# NetArchitect: Recommendation & Config Engine

**NetArchitect** is an academic Computer Networks project engineered to provide automated, algorithmically driven network planning, physical media recommendation, hierarchical IP address allocation (VLSM), routing protocol design, and multi-vendor CLI configuration generation.

---

## 1. Academic & Architectural Overview

The engine bridges theoretical Computer Networks principles with real-world infrastructure deployment. Its design revolves around four core pillars:

1. **Physical Transmission Media Selection (Layer 1)**: Evaluates link distance, throughput, EMI susceptibility, and cost across Twisted Pair Copper (Cat5e/Cat6/Cat6a), Optical Fiber (Multi-mode OM3/OM4, Single-mode OS2), and Wireless.
2. **Hierarchical IP Planning & VLSM (Layer 3)**: Implements Variable Length Subnet Masking (RFC 1878, RFC 4632) to conserve address space and prevent subnet overlapping.
3. **Routing Protocol Optimization (Layer 3)**: Selects between Interior Gateway Protocols (OSPF v2/v3) and Exterior Gateway Protocols (BGP-4) based on AS scale, convergence deadlines, and topology diameter.
4. **Transparent Explainability & Standards Audit**: Every architectural decision is paired with technical reasoning, governing RFCs (e.g. RFC 2328, RFC 4271), and IEEE standards.

### Mandatory Network Profiles

NetArchitect natively models three distinct network tiers:
* **Campus LAN**: High throughput (1–10 Gbps), ultra-low latency (< 5 ms), copper access drops with fiber backbone, IEEE 802.1Q VLANs, and single/multi-area OSPF.
* **Metro MAN**: City-wide interconnects (5–50 km), Carrier Ethernet / Dark Fiber, 1–40 Gbps, QinQ, and MPLS/OSPF.
* **Global WAN**: Long-haul multi-regional links (> 100 km), submarine/leased lines, SD-WAN overlays, IPSec tunnels, and BGP-4 peering.

### Physical Media Recommendation Engine (Phase 3)

The Physical Media Recommendation Engine (`MediaEngine`) implements deterministic Layer 1 selection under IEEE 802.3 and ANSI/TIA standards:

#### 1. Distance Tiers & Optical Reach Decision
* **$\le 100\text{ m}$**: **Cat6a Balanced Twisted Pair** (10GBASE-T, IEEE 802.3an). Maximum channel insertion loss $\le 49.3\text{ dB}$ at 500 MHz (ANSI/TIA-568-C.2).
* **$101\text{--}400\text{ m}$**: **OM4 Multimode Fiber (50/125 µm)** (10GBASE-SR, IEEE 802.3ae). Operates at 850 nm with VCSEL laser optics and 4700 MHz·km Effective Modal Bandwidth (EMB).
* **$401\text{--}10,000\text{ m}$**: **OS2 Single-Mode Fiber (9/125 µm)** (10GBASE-LR, IEEE 802.3ae Clause 52). Operates at 1310 nm with DFB lasers up to 10 km. Available optical budget: 6.2 dB ($P_{\text{tx\_min}} = -8.2\text{ dBm}, P_{\text{rx\_sens}} = -14.4\text{ dBm}$).
* **$10,001\text{--}40,000\text{ m}$**: **OS2 Single-Mode Fiber Extended** (10GBASE-ER, IEEE 802.3ae Clause 52). Operates at 1550 nm with cooled DFB/EML lasers up to 40 km. Available optical budget: 11.1 dB ($P_{\text{tx\_min}} = -4.7\text{ dBm}, P_{\text{rx\_sens}} = -15.8\text{ dBm}$).
* **$> 40,000\text{ m}$**: Raises `PhysicalDistanceViolationError` (HTTP 400). Standard unamplified point-to-point Ethernet links cannot exceed 40 km without active optical line amplification (EDFA) or DWDM transponders.

#### 2. Preferred-Medium Policy
| Tier / Distance Range | Preferred Copper | Preferred Multimode (OM4) | Preferred Single-Mode (OS2) |
|---|---|---|---|
| **$\le 100\text{ m}$** | Cat6a Copper (Default) | Honored (OM4 MMF, EMI immunity) | Honored (OS2 SMF, future-proofing) |
| **$101\text{--}400\text{ m}$** | **Violation (Error 400)** | OM4 MMF (Default) | Honored (OS2 SMF, 10GBASE-LR) |
| **$401\text{--}10,000\text{ m}$** | **Violation (Error 400)** | **Violation (Error 400)** | OS2 SMF 10GBASE-LR (Default) |
| **$10,001\text{--}40,000\text{ m}$** | **Violation (Error 400)** | **Violation (Error 400)** | OS2 SMF 10GBASE-ER (Default) |
| **$> 40,000\text{ m}$** | **Violation (Error 400)** | **Violation (Error 400)** | **Violation (Error 400, > 40 km)** |

*Incompatible preferences never silently fall back to another medium.*

#### 3. Standard Specifications vs. Engineering Estimates
* **Standard-Defined Specifications**: IEEE 802.3an channel length (100m) and loss (49.3 dB at 500 MHz); IEEE 802.3ae transceiver parameters (10GBASE-LR: 1310 nm, 6.2 dB budget; 10GBASE-ER: 1550 nm, 11.1 dB budget); TIA-492AAAD EMB (4700 MHz·km).
* **Engineering Assumptions & Estimates**: Fiber attenuation modeled as conservative estimates of 0.4 dB/km at 1310 nm and 0.25 dB/km at 1550 nm (ITU-T G.652.D); connector loss modeled at 1.0 dB (two mated LC duplex pairs @ 0.5 dB each per TIA-568-C.3); engineering safety margin modeled at 3.0 dB.
* **Optical Budget Sufficiency vs. Standard Reach**:
  - At **850 m (LR)**: Estimated loss $4.34\text{ dB} \le 6.2\text{ dB}$ budget $\rightarrow$ `is_budget_sufficient: True` ($+1.86\text{ dB}$ margin).
  - At **10,000 m (LR)**: Estimated loss $8.00\text{ dB} > 6.2\text{ dB}$ budget $\rightarrow$ `is_budget_sufficient: False` ($-1.80\text{ dB}$ deficit under conservative assumptions; standard 10 km reach is preserved, but requires link engineering optimization).
  - At **10,001 m (ER)**: Estimated loss $6.50\text{ dB} \le 11.1\text{ dB}$ budget $\rightarrow$ `is_budget_sufficient: True` ($+4.60\text{ dB}$ margin).
  - At **40,000 m (ER)**: Estimated loss $14.00\text{ dB} > 11.1\text{ dB}$ budget $\rightarrow$ `is_budget_sufficient: False` ($-2.90\text{ dB}$ deficit under conservative assumptions; requires premium $\le 0.20\text{ dB/km}$ fiber or fusion splices).

### VLSM & Subnetting Engine (Phase 4)

The Variable Length Subnet Masking Engine (`VLSMEngine`) performs optimal, fragmentation-free hierarchical IPv4 address allocation under **RFC 1878** and **RFC 4632**:

#### 1. Core Algorithmic Principles
* **Descending Host-Count Sorting**: Requirements are sorted in descending order ($H_1 \ge H_2 \ge \dots \ge H_n$) prior to allocation. This guarantees that larger subnets with strict binary power-of-two boundaries are allocated first, preventing address space fragmentation and alignment collisions.
* **Prefix Sizing Formula**: Finds the smallest host bit count $h \ge 2$ satisfying $2^h - 2 \ge H_{\text{required}}$, with prefix length $p = 32 - h$. Subnets reserve the first address as Network ID and the last address as Directed Broadcast.
* **Mathematical Alignment & Zero Overlap**: Every subnet network address integer $N$ is strictly aligned to a multiple of its block size: $N \pmod{2^h} == 0$.
* **Default Gateway Convention**: The **first usable host IP address** in each allocated subnet range is systematically designated as the default gateway.
* **Contiguous Remaining Address Space**: Unallocated address space is summarized into minimal contiguous valid CIDR blocks via `ipaddress.summarize_address_range`.
* **Address Space Exhaustion**: If requested subnets exceed root network capacity, raises `InsufficientAddressSpaceError` (HTTP 400).

### Routing Decision Engine (Phase 5)

The Routing Decision Engine (`RoutingEngine`) implements deterministic, standards-based routing architecture selection under **RFC 2328** (OSPF Version 2) and **RFC 4271** (Border Gateway Protocol 4):

#### 1. Supported Architectures
* **Single-Area OSPF (Area 0)**:
  - Recommended for single Autonomous System (AS = 1), internal routing domains with fewer than 50 subnets.
  - All interfaces reside in Area 0 (Backbone 0.0.0.0) and maintain identical Link-State Databases (LSDB).
  - Every router independently executes Dijkstra's Shortest Path First (SPF) algorithm to calculate loop-free shortest paths based on interface cost.
  - Minimal operational overhead: no Area Border Routers (ABRs) or inter-area summarization required.
* **Multi-Area OSPF**:
  - Recommended for single Autonomous System (AS = 1) networks where multiple internal areas are explicitly required.
  - Implements a two-tier hierarchy centered around a mandatory Area 0 backbone.
  - Area Border Routers (ABRs) maintain separate LSDBs for each attached area, inject Type 3 Summary LSAs into adjacent areas, and contain link flaps (SPF calculations are confined to the originating area).
* **eBGP (External Border Gateway Protocol)**:
  - Recommended whenever multiple Autonomous Systems are present ($AS > 1$) or an external AS routing boundary exists.
  - Path-vector routing operating over TCP port 179; uses the `AS_PATH` attribute for loop prevention and administrative policy controls (Local Preference, MED, AS prepending).
  - **Academic Principle**: eBGP does **NOT** replace internal routing protocols. An Interior Gateway Protocol (such as OSPF) is still strictly required within each AS to distribute internal subnets and resolve BGP recursive next-hop IP addresses.
* **Design Review Diagnostics**:
  - When topology inputs are contradictory (e.g. multiple ASes specified but `has_external_as_boundary=False`) or underspecified (e.g. $\ge 50$ subnets without explicit area partitioning), the engine returns a structured design review result rather than making unverified assumptions.

#### 2. Deterministic Decision Precedence Hierarchy
```
1. Contradiction Check: If AS > 1 and has_external_as_boundary == False -> Design Review Required
2. Rule 1 (Inter-AS / External Boundary Precedence): If AS > 1 or has_external_as_boundary == True -> eBGP
3. Rule 2 (Multi-Area OSPF Precedence): If AS == 1 and ospf_areas_required > 1 -> Multi-Area OSPF
4. Rule 3 (Single-Area OSPF Precedence): If AS == 1, subnets < 50, and areas in (None, 1) -> Single-Area OSPF (Area 0)
5. Rule 4 (Scale Boundary Review): If AS == 1, subnets >= 50, and areas is None -> Design Review Required
```

#### 3. Standard Specifications vs. Operational Design Heuristics
* **Standard-Defined Specifications**: RFC 2328 defines OSPFv2 protocol mechanics (LSDB flooding, Dijkstra's algorithm, Area 0 backbone, ABR Type 3 LSAs); RFC 4271 defines BGP-4 path-vector exchange and AS_PATH loop detection.
* **Engineering Scalability Heuristics**: The **50-subnet threshold** is an operational guideline to prevent excessive Dijkstra SPF recalculation overhead and large LSDB memory footprints in flat single-area networks. RFC 2328 itself does not prescribe a rigid numerical limit.
* **Multi-Site Networks**: Multi-site networks within a single Autonomous System do **not** automatically mandate BGP. Enterprise branch sites connected via private Metro Ethernet or dark fiber operate cleanly under an internal IGP (OSPF).

### Configuration Generation Engine (Phase 6)

The Configuration Generation Engine (`ConfigGenerator`) produces syntax-valid, modular Cisco IOS / IOS-XE configuration templates by compiling validated topologies and outputs from the Layer 1 Media, Layer 3 VLSM, and Routing Decision engines:

#### 1. Supported Configuration Sections
* **System Management & Security**: Hostname definition, domain-lookup suppression (`no ip domain-lookup`), high-resolution logging timestamps (`service timestamps log datetime msec`), and encrypted management lines (`transport input ssh`).
* **VLAN Tagging (IEEE 802.1Q)**: Explicit VLAN instantiation in the VLAN database, access port assignments (`switchport mode access`, `switchport access vlan <id>`), dot1q trunking (`switchport mode trunk`), and restricted allowed VLAN lists (`switchport trunk allowed vlan <list>`).
* **Layer 3 Interface Addressing**: IP address and dotted-decimal subnet mask assignment on physical routed ports, sub-interfaces, and Management Switch Virtual Interfaces (SVI / `interface Vlan1`). Default gateway definition for Layer 2 switches (`ip default-gateway`).
* **Single-Area OSPF**: OSPF process initialization, static 32-bit Router ID (`router-id`), adjacency logging, passive interface restrictions, and Area 0 network statements (RFC 2328).
* **Multi-Area OSPF**: Hierarchical area definitions with Area 0 as the mandatory backbone, non-backbone area statements, and Area Border Router (ABR) boundary configuration.
* **eBGP Peering**: Inter-Autonomous System path-vector configuration (`router bgp <asn>`), static BGP router ID, verified neighbor statements (`neighbor <ip> remote-as <remote_as>`), neighbor descriptions, and explicit network prefix masks (RFC 4271).

#### 2. Validation & Safety Enforcement
* **Zero Credential Exposure**: Strictly disallows plaintext passwords, secrets, or privileged keys in inputs and generated configuration files.
* **Integrity Validation**: Detects duplicate interface names, duplicate VLAN IDs, assignments to undeclared VLANs, non-zero areas under Single-Area OSPF, and missing/invalid BGP neighbors.
* **Academic Simulation Notice**: Explicitly banners that configurations are synthesized simulation templates requiring human administrator review prior to physical hardware deployment.
* **Secure Artifact Export**: Automatically writes verified `.cfg` and `.txt` files to `backend/exports/` using sanitized hostnames and strict path-traversal prevention. Available for download via `GET /api/v1/configs/{config_id}/download`.

---

## 2. Project Directory Structure

The project maintains complete decoupling between the FastAPI backend and React frontend, allowing both to be run, tested, and demonstrated independently.

```
NetArchitect/
├── README.md                          # Comprehensive project documentation
├── .gitignore                         # Project-wide ignore rules
│
├── backend/
│   ├── venv/                          # Python 3.12 virtual environment
│   ├── requirements.txt               # Backend dependencies
│   ├── main.py                        # FastAPI entrypoint with CORS & route mounting
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/                    # API endpoints
│   │       ├── __init__.py            # Master router aggregator (/api/v1)
│   │       ├── health.py              # Health check endpoint
│   │       ├── scenarios.py           # Network profile endpoints (Campus LAN, Metro MAN, Global WAN)
│   │       ├── media.py               # Layer 1 media recommendation routes
│   │       ├── subnetting.py          # VLSM & CIDR computation routes
│   │       ├── routing.py             # Routing protocol recommendation routes
│   │       └── configs.py             # Device configuration generation routes
│   │
│   ├── engines/                       # Dedicated algorithm modules
│   │   ├── __init__.py
│   │   ├── media_engine.py            # Physical transmission media selection engine
│   │   ├── vlsm_engine.py             # VLSM & IP partitioning engine
│   │   ├── routing_engine.py          # OSPF/BGP routing selection engine
│   │   ├── explainability_engine.py   # Decision audit logging & RFC citation engine
│   │   └── config_generator.py        # Cisco IOS & CLI script generator engine
│   │
│   ├── services/                      # Orchestration & business logic layer
│   │   ├── __init__.py
│   │   └── scenario_service.py        # Manages Campus LAN, Metro MAN, Global WAN profiles
│   │
│   ├── models/                        # Pydantic domain & request/response schemas
│   │   ├── __init__.py
│   │   ├── scenario.py                # Network profile models
│   │   ├── media.py                   # Media recommendation schemas
│   │   ├── subnet.py                  # VLSM request/allocation schemas
│   │   ├── routing.py                 # Routing protocol recommendation schemas
│   │   ├── config.py                  # CLI config generation schemas
│   │   └── explanation.py             # Decision audit log schemas
│   │
│   ├── data/                          # Reference catalogs & baseline profiles
│   │   ├── __init__.py
│   │   ├── network_profiles.json      # Profile specifications
│   │   └── device_catalog.json        # Switch & router hardware specifications
│   │
│   ├── utils/                         # Shared helper utilities
│   │   ├── __init__.py
│   │   ├── ip_helpers.py              # IPv4/CIDR validation and bitmask calculations
│   │   └── logger.py                  # Structured application logger
│   │
│   ├── tests/                         # Pytest test suite
│   │   ├── __init__.py
│   │   ├── conftest.py                # Fixtures
│   │   └── test_health.py             # Endpoints, CORS, and engine validation tests
│   │
│   └── exports/                       # Destination for generated .cfg files
│       └── .gitkeep
│
└── frontend/
    ├── package.json                   # Dependencies & scripts
    ├── vite.config.js                 # Vite build configuration
    ├── index.html                     # HTML template
    ├── .env                           # Environment configuration (VITE_API_URL)
    ├── .env.example
    │
    └── src/
        ├── main.jsx                   # React application mounting
        ├── App.jsx                    # Root view rendering Layout & Dashboard
        ├── index.css
        │
        ├── layouts/
        │   └── MainLayout.jsx         # Header, status badge, and academic footer
        │
        ├── components/
        │   └── common/
        │       ├── Navbar.jsx         # App navigation header
        │       └── StatusBadge.jsx    # Real-time backend connectivity badge
        │
        ├── pages/
        │   └── Dashboard.jsx          # Academic dashboard & engine module overview
        │
        ├── services/
        │   ├── api.js                 # Base API client
        │   └── healthService.js       # Backend /health API client
        │
        ├── hooks/
        │   └── useBackendHealth.js    # Custom React hook for live FastAPI connectivity
        │
        └── data/
            ├── networkProfiles.js     # Campus LAN, Metro MAN, Global WAN metadata
            └── engineModules.js       # Module directory & status registry
```

---

## 3. Setup and Execution Instructions

### Prerequisites
- **Python**: 3.12+ (existing virtual environment located in `backend/venv`)
- **Node.js**: 18+ and `npm`

---

### Running the Backend (FastAPI)

1. Open a terminal and navigate to the `backend` directory:
   ```powershell
   cd backend
   ```

2. Activate the existing virtual environment:
   * **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * **Windows (CMD)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   * **Linux/macOS**:
     ```bash
     source venv/bin/activate
     ```

3. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. Verify in browser:
   * **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   * **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
   * **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Running the Frontend (React + Vite)

1. Open a separate terminal and navigate to the `frontend` directory:
   ```powershell
   cd frontend
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```

3. Open the frontend in your browser:
   * [http://localhost:5173/](http://localhost:5173/)

4. The dashboard will automatically ping the backend at `http://127.0.0.1:8000/health` and display a green **"Backend Online"** badge with round-trip latency.

---

### CORS Configuration

The backend is configured in `backend/main.py` with `CORSMiddleware` to allow requests from:
- `http://localhost:5173`
- `http://127.0.0.1:5173`

---

## 4. Running Tests and Quality Checks

### Backend Automated Tests (Pytest)
Run the test suite from the repository root:
```powershell
backend\venv\Scripts\pytest.exe backend\tests -v
```
Or with the virtual environment activated:
```bash
pytest backend/tests -v
```

### Frontend Linting & Production Build
To verify code formatting and production compilation:
```bash
cd frontend
npm run lint
npm run build
```

---

## 5. Next Phase Roadmap
- **Phase 3**: Physical Transmission Media Recommendation Engine (`engines/media_engine.py`) — **COMPLETED**
- **Phase 4**: VLSM & Hierarchical Subnetting Calculation Engine (`engines/vlsm_engine.py`) — **COMPLETED**
- **Phase 5**: Routing Decision & Architecture Engine (`engines/routing_engine.py`) — **COMPLETED**
- **Phase 6**: Cisco IOS Device Configuration Generator (`engines/config_generator.py`) — **COMPLETED**
- **Phase 7**: Link explainability logs to interactive frontend views for academic demonstration.
