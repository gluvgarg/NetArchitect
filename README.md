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
- **Phase 2**: Implement deterministic Layer 1 Media Selection logic in `engines/media_engine.py`.
- **Phase 3**: Implement VLSM calculation algorithm with subnet partitioning in `engines/vlsm_engine.py`.
- **Phase 4**: Implement routing protocol heuristics (OSPF Area design vs BGP peering) in `engines/routing_engine.py`.
- **Phase 5**: Implement Cisco IOS configuration generator in `engines/config_generator.py` and export scripts to `backend/exports/`.
- **Phase 6**: Link explainability logs to interactive frontend views for academic demonstration.
