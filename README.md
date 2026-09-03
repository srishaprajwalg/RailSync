# RailVyuha

**AI-Assisted Railway Maintenance Block Planning & Decision Support System**

**Problem Statement Reference:** SIH26027 — AI-Powered Automatic Block Planning to Maximize Asset Availability for Train Operations on Indian Railways.

---

## 1. Overview

RailVyuha is an AI-assisted decision-support platform designed to assist railway operations controllers and maintenance engineers in planning and scheduling track maintenance blocks. 

In railway networks, maintenance work (track tamping, OHE inspection, signaling repairs, rail replacement) requires blocking traffic on specific track sections for designated durations. Scheduling these blocks manually across separate departments (Engineering, S&T, Traction) is challenging due to dense passenger schedules, freight train movements, and tight headway windows.

RailVyuha addresses this challenge by providing an end-to-end, data-driven workflow that:
- Prioritizes maintenance requests using deterministic, auditable scoring augmented by machine learning failure-risk indicators.
- Analyzes passenger timetables and freight forecast envelopes to identify conflict-free maintenance intervals.
- Solves maintenance block schedules using **Google OR-Tools CP-SAT** constraint programming.
- Consolidates compatible departmental tasks into unified maintenance blocks while enforcing strict spatial limits and physical safety margins.
- Generates explicit mathematical explanations for infeasible or deferred tasks.
- Visualizes train movements, freight occupancy, and planned maintenance blocks in an interactive web dashboard.

> **Note on System Role:** RailVyuha is a decision-support and planning optimization tool intended to aid human railway controllers. It is not an autonomous train control system and does not directly command signaling or field interlocking hardware.

---

## 2. Core Workflow

The scheduling pipeline operates through the following stages:

```mermaid
flowchart TD
    subgraph Data_Layer["1. Infrastructure & Maintenance Inputs"]
        Infrastructure["Corridors, Sections, Stations, Assets"]
        Timetables["Passenger Timetables & Freight Forecasts"]
        Requests["Maintenance Requests (Engineering, S&T, Traction)"]
    end

    subgraph Intelligence_Layer["2. Risk Assessment & Priority Scoring"]
        ML["Recurrence & Failure Risk Prediction (Logistic Regression)"]
        Prio["Explainable Priority Engine (Deterministic 0-100 Score)"]
        ML --> Prio
        Requests --> Prio
    end

    subgraph Solver_Layer["3. Feasibility & Constraint Scheduling"]
        Feasibility["Headway & Deadline Feasibility Analysis"]
        CPSAT["Google OR-Tools CP-SAT Solver"]
        Timetables --> Feasibility
        Prio --> Feasibility
        Feasibility --> CPSAT
    end

    subgraph Consolidation_Layer["4. Safety-Aware Block Consolidation"]
        Grouping["Multi-Department Task Grouping"]
        SafetyValidation["Envelope Clearance & Max Span Enforcement (<= 20 km)"]
        CPSAT --> Grouping
        Grouping --> SafetyValidation
    end

    subgraph Presentation_Layer["5. Persistence & Decision Support UI"]
        DB["PostgreSQL / PostGIS Database"]
        UI["Interactive Dashboard, String Charts & Dispatcher Overrides"]
        SafetyValidation --> DB
        DB --> UI
    end
```

1. **Infrastructure & Workload Ingestion**: Loads corridor geometry, stations, track sections, physical assets, active maintenance requests, and train path schedules.
2. **Maintenance Risk Prioritization**: Computes deterministic priority scores (0–100) combining severity, asset criticality, overdue days, deadline urgency, and ML recurrence risk.
3. **Timetable & Freight Conflict Analysis**: Models passenger train arrival/departure trajectories and freight forecast uncertainty windows to determine available track headways with a 15-minute safety buffer.
4. **CP-SAT Mathematical Scheduling**: The constraint solver acts as the primary scheduling authority, assigning optimal start times that maximize high-priority task coverage while respecting non-overlap constraints with train paths.
5. **Safety-Aware Block Consolidation**: Post-solver algorithms consolidate spatially and temporally compatible departmental tasks into unified maintenance blocks, strictly enforcing physical envelope clearance and a 20 km maximum block span.
6. **Infeasibility Explanation & Persistence**: Requests that cannot fit before deadlines receive mathematical explanations based on train density and available continuous headway. All runs, blocks, tasks, and decisions are persisted in PostgreSQL.
7. **Dispatcher Review & Visualization**: Operations staff inspect time-distance string charts, evaluate block consolidation efficiency, and can override task priorities with an auditable justification trail.

---

## 3. Multi-Corridor Architecture

RailVyuha supports independent, partitioned planning across multiple railway corridors. All data models, queries, optimization runs, and APIs are isolated by corridor identifier:

| Corridor ID | Route | Distance | Stations | Line Configuration |
| :--- | :--- | :--- | :--- | :--- |
| **`SBC-JTJ`** | KSR Bengaluru → Jolarpettai | 145.0 km | 7 stations (`SBC`, `BNC`, `KJM`, `WFD`, `BWT`, `KPN`, `JTJ`) | Double Line Electrified Trunk (SWR / SR) |
| **`NDLS-CNB`** | New Delhi → Kanpur Central | 440.0 km | 6 stations (`NDLS`, `GZB`, `ALJN`, `TDL`, `ETW`, `CNB`) | High-Density Quad-Track Trunk Route (NCR) |
| **`CSTM-PUNE`** | Mumbai CST → Pune Junction | 192.0 km | 5 stations (`CSTM`, `KYN`, `KJT`, `LNL`, `PUNE`) | Bhor Ghat Mountain Section / Heavy Gradient (CR) |

### Corridor Isolation Guarantees
- **Database Partitioning**: Foreign keys enforce corridor ownership across sections, assets, maintenance requests, train runs, freight forecasts, optimization runs, and planned blocks.
- **Solver Isolation**: CP-SAT executes independently per corridor. Train movements on one corridor cannot affect or contaminate scheduling on another.
- **API Partitioning**: All retrieval and mutation endpoints require or filter by `corridor_id`.
- **UI Dynamic Switching**: The frontend corridor selector dynamically reloads all infrastructure maps, timetable string charts, workload statistics, and planned blocks for the selected corridor.

---

## 4. Data Sources and Provenance

RailVyuha maintains a clear distinction between real external datasets and synthetic operational demo data:

| Entity Type | Provenance | Source / Methodology |
| :--- | :--- | :--- |
| **Stations & Coordinates** | Real Dataset | Sourced from the public [Datameet Indian Railways repository](https://github.com/datameet/railways) (`stations.json`). Station coordinates and names reflect actual railway locations. |
| **Route Geometry & Chainage** | Real Dataset / Calibrated | Cumulative Haversine distances between sequential stations are computed from geographic coordinates and scaled proportionally to match official route kilometer markers. |
| **Passenger Timetables** | Real Dataset | Sourced from Datameet (`schedules.json`, covering ~417k schedule records). Filtered for strictly monotonic traversing trains across each corridor, classified by service type (Vande Bharat, Shatabdi, Superfast, Express, Passenger), and projected over the operational planning horizon. |
| **Maintenance Requests** | Synthetic / Demo Data | Synthetically generated to reflect realistic Indian Railways Track Management System (TMS), Signaling Maintenance Management System (SMMS), and Traction Distribution Management System (TDMS) defect and routine maintenance patterns across Engineering, S&T, and Traction departments. |
| **Maintenance History & Failures** | Synthetic / Demo Data | Synthetically generated logs of prior repairs, inspection events, and defect recurrences used for demonstrating ML training and risk estimation. |
| **Freight Train Forecasts** | Synthetic / Demo Data | Synthetically generated entry/exit time windows with spatial boundaries reflecting goods train traffic patterns. |
| **Physical Assets** | Synthetic / Demo Data | Synthetically generated inventory of track segments, points, signals, OHE sub-sectors, and bridges associated with corridor sections. |

> **Disclaimer:** The Datameet dataset is an open-source community repository and is not an official Indian Railways API. Maintenance requests, asset records, and freight forecasts are synthetic demonstration data. RailVyuha does not currently integrate directly with live production Indian Railways TMS, SMMS, or TDMS databases.

---

## 5. Database Architecture

The persistence layer is built on **PostgreSQL** with **PostGIS** spatial capabilities, managed through **SQLAlchemy 2.0** ORM and **Alembic** database migrations.

### Core Relational Schema

```
┌────────────────────────────────────────────────────────────────────────┐
│                          INFRASTRUCTURE                                │
│  corridors ──< sections ──< stations                                   │
│      │             │                                                   │
│      │             └──< assets ──< maintenance_history                 │
│      │                                                                 │
│      ├──< train_runs ──< train_movements                               │
│      ├──< freight_forecasts                                            │
│      │                                                                 │
│      └──< maintenance_requests ──< ml_predictions                      │
│                 │              ──< priority_decisions                  │
│                 │                                                      │
│                 └──< block_tasks >── planned_blocks ──< outcomes       │
│                                            │                           │
│                 schedule_decisions ────────┘                           │
│                          ▲                                             │
│                          └── optimization_runs                         │
└────────────────────────────────────────────────────────────────────────┘
```

- **`corridors`**: Multi-corridor registry with route codes, display names, and total route lengths.
- **`sections`**: Track subdivisions with start/end chainages and track directions.
- **`stations`**: Station nodes with geographic coordinates (`latitude`, `longitude`) and calibrated chainages.
- **`assets`**: Track, signal, point, OHE, and bridge infrastructure records assigned to maintenance departments (`ENGINEERING`, `S&T`, `TRACTION`).
- **`trains` & `train_runs`**: Catalog of passenger trains and their scheduled corridor service runs.
- **`train_movements`**: Scheduled arrival, departure, and passage times at individual stations.
- **`freight_forecasts`**: Time-window forecasts for freight paths with spatial extents.
- **`maintenance_requests`**: Maintenance work orders with lifecycle states (`OPEN`, `PRIORITIZED`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `DEFERRED`).
- **`maintenance_history`**: Historical records of prior maintenance events, repair durations, failure types, and recurrence outcomes.
- **`ml_predictions`**: Versioned inference audit records capturing feature snapshots and recurrence probabilities.
- **`priority_decisions`**: Persisted mathematical breakdowns of priority scores with explainable factor contributions.
- **`optimization_runs`**: Solver execution audit logs tracking solve durations, solver parameters, and timing breakdowns.
- **`planned_blocks`**: Consolidated physical maintenance block reservations with time windows and chainage spans.
- **`block_tasks`**: Associative table linking maintenance requests to their assigned planned blocks.
- **`schedule_decisions`**: Detailed operational reasoning recorded for each scheduled task assignment.
- **`maintenance_outcomes`**: Post-execution feedback recording actual maintenance duration, completion status, and train delays.

---

## 6. Machine Learning Pipeline

### Model Architecture
The failure risk component uses **Logistic Regression** (implemented via `scikit-learn`) to estimate the probability of defect recurrence on a given asset.

### Feature Specification (`FEATURE_VERSION = "recurrence_features_v2"`)
Both offline training (`backend/services/ml_training_pipeline.py`) and online inference (`backend/services/ml_engine.py`) use an identical 8-dimensional feature vector:

1. **`asset_age_years`** (`float`): Age of the asset in years computed from installation date.
2. **`asset_criticality`** (`float`): Operational criticality rank of the asset ($1\text{--}5$).
3. **`past_failures_count`** (`float`): Total past failure/emergency events logged on this asset strictly prior to observation time $T$.
4. **`recurrence_ratio`** (`float`): Ratio of prior events on this asset where recurrence was confirmed ($\frac{\text{recurrent\_events}}{\text{total\_events}}$).
5. **`avg_past_duration_hrs`** (`float`): Historical average duration in hours of prior repair events on this asset.
6. **`time_since_last_failure_days`** (`float`): Days elapsed since the most recent failure on this asset before observation time $T$.
7. **`request_severity`** (`float`): Severity level of the incoming maintenance request ($1\text{--}5$).
8. **`is_defect`** (`float`): Binary indicator ($1$ for unplanned defect repair, $0$ for scheduled routine maintenance).

### Leakage Prevention
Training datasets are constructed using strict temporal observation boundaries:
$$\text{Observation Time } T \longrightarrow \text{Features strictly available at or before } T \longrightarrow \text{Future recurrence target } y \in \{0, 1\}$$
Future repair durations, subsequent defect occurrences, and post-maintenance outcomes are explicitly excluded from the feature set.

### Validation & Fallback Handling
- When historical data is sparse ($N < 15$ samples or $< 2$ target classes), the validation pipeline flags `INSUFFICIENT_DATA_FOR_VALIDATION` and utilizes a documented bootstrap synthetic calibration dataset to establish reasonable baseline coefficients.
- When sufficient data exists ($N \ge 15$), stratified cross-validation evaluates precision, recall, F1-score, and ROC-AUC against:
  1. Majority-class baseline predictor
  2. Deterministic rule-based heuristic

> **ML Calibration Notice:** Because current maintenance history data is synthetically generated for demonstration, the resulting model weights and prediction probabilities reflect synthetic calibration and must not be interpreted as empirically validated against real-world Indian Railways field failure rates.

---

## 7. Explainable Prioritization

RailVyuha computes a deterministic, fully auditable priority score ($0\text{--}100$) for every maintenance request. The score combines rule-based operational criteria with ML risk output:

$$\text{Priority Score} = S_{\text{severity}} + S_{\text{criticality}} + S_{\text{overdue}} + S_{\text{urgency}} + S_{\text{ml\_risk}}$$

### Factor Contributions
- **Severity Score ($0\text{--}30$ pts)**: Derived from request severity level ($1\text{--}5$) and defect type. Defects receive higher baseline weighting than routine inspections.
- **Asset Criticality Score ($0\text{--}10$ pts)**: Reflects physical asset importance ($1\text{--}5$) scaled to operational risk.
- **Overdue Score ($0\text{--}20$ pts)**: Scaled by days past scheduled maintenance window ($\min(20, \text{overdue\_days} \times 2)$).
- **Urgency Score ($0\text{--}20$ pts)**: Calculated from time remaining until deadline:
  - $< 24$ hours: $+20$ pts
  - $24\text{--}72$ hours: $+12$ pts
  - $3\text{--}7$ days: $+6$ pts
  - $> 7$ days: $+2$ pts
- **ML Recurrence Risk Contribution ($0\text{--}10$ pts)**: Scales the logistic regression prediction probability: $\text{round}(P(\text{recurrence}) \times 10)$.

### Priority Categories
- **Critical**: Score $\ge 70$
- **High**: Score $50\text{--}69$
- **Medium**: Score $30\text{--}49$
- **Low**: Score $< 30$

Every priority calculation persists an auditable breakdown in `priority_decisions`, providing human-readable explanations of each factor's point contribution.

---

## 8. Mathematical Optimization (CP-SAT)

The scheduling engine uses **Google OR-Tools CP-SAT** as the authoritative mathematical solver.

### Optimization Model Formulation

#### Decision Variables
For each eligible maintenance task $i$:
- $\text{start}_i \in [0, \text{effective\_deadline}_i - \text{duration}_i]$
- $\text{end}_i = \text{start}_i + \text{duration}_i$
- $\text{interval}_i = \text{NewIntervalVar}(\text{start}_i, \text{duration}_i, \text{end}_i)$
- $\text{scheduled}_i \in \{0, 1\}$ (optional interval presence)

#### Hard Constraints
1. **Passenger Train Path Clearance**: For every scheduled passenger train occupying the task's chainage $[k_{\min}, k_{\max}]$ during interval $[t_{\text{arr}}, t_{\text{dep}}]$, the maintenance interval must not overlap:
   $$\text{NoOverlap}(\text{interval}_i, [t_{\text{arr}} - \Delta_{\text{safety}}, t_{\text{dep}} + \Delta_{\text{safety}}])$$
   where $\Delta_{\text{safety}} = 15$ minutes.
2. **Freight Path Clearance**: For every freight forecast envelope $[t_{\text{entry}}, t_{\text{exit}}]$ intersecting the task's chainage, an identical 15-minute safety buffer is enforced.
3. **Deadlines & Time Horizons**: $\text{end}_i \le \min(\text{deadline}_i, \text{horizon\_mins})$.
4. **Department Resource Capacities**: Simultaneous work within the same department and corridor is constrained by resource availability bounds.

#### Objective Function Structure
The CP-SAT model optimizes a multi-tiered hierarchical objective:
$$\max \sum_{i} \left( W_{\text{coverage}} \cdot \text{scheduled}_i + W_{\text{priority}} \cdot \text{priority}_i \cdot \text{scheduled}_i - W_{\text{earliness}} \cdot \text{start}_i \right)$$
- **Primary Goal**: Maximize the number of scheduled maintenance tasks.
- **Secondary Goal**: Prioritize critical and high-scoring tasks over low-priority tasks.
- **Tertiary Goal**: Encourage earlier completion within the planning window when multiple conflict-free headways are available.

---

## 9. Safety-Aware Block Consolidation

After the CP-SAT solver assigns optimal conflict-free execution intervals to individual maintenance tasks, a dedicated block consolidation algorithm groups compatible tasks into unified physical maintenance blocks.

### Consolidation Rules
1. **Line Direction Compatibility**: Only tasks on the same track direction (`Up` or `Down`) can share a block.
2. **Temporal Overlap**: Task scheduled intervals must overlap or abut within the protected block window.
3. **Spatial Adjacency**: Task chainage extents must overlap or be spatially contiguous.
4. **Inter-Departmental Compatibility**: Rules verify that concurrent activities (e.g., track tamping and overhead wire inspection) can safely operate together.
5. **Physical Span Constraint ($\le 20.0$ km)**: The combined physical envelope of any consolidated block cannot exceed **20.0 km**:
   $$\max_{i \in \text{group}}(k_{\max, i}) - \min_{i \in \text{group}}(k_{\min, i}) \le 20.0 \text{ km}$$
6. **Graph Transitivity Enforcement**: When connected-component grouping produces a cluster exceeding 20 km through chained pairwise edges, the cluster is automatically partitioned into compliant sub-clusters of $\le 20.0$ km.
7. **Post-Consolidation Clearance Verification**: Every consolidated block's total envelope $[k_{\min}, k_{\max}] \times [t_{\text{start}}, t_{\text{end}}]$ is independently checked against all passenger and freight occupancies with the 15-minute safety buffer before registration.
8. **Task Conservation**: Every task submitted to the optimizer is strictly accounted for. Tasks that cannot be scheduled are classified as either **Infeasible** (deadline or headway mathematically impossible) or **Deferred** (resource or capacity contention), with zero silent task drops.

---

## 10. Infeasibility & Rejection Explanations

When a maintenance request cannot be scheduled within its requested parameters, RailVyuha generates an explicit mathematical explanation rather than a generic failure status:

- **Duration Exceeds Deadline**: Explains that the requested task duration ($D$ mins) strictly exceeds the available time before the effective deadline.
- **Insufficient Train Headway**: Calculates the maximum continuous available headway gap ($G_{\max}$ mins) across all train passes within the corridor section, explaining that $G_{\max} < D + 2 \times \Delta_{\text{safety}}$ prevents safe insertion.
- **Dense Traffic Density**: Identifies the total count of conflicting train paths during the active window that obstruct continuous track possession.

---

## 11. Dispatcher Overrides & Auditability

Railway operations controllers retain full authority to override automated priority scores:

- **API Endpoint**: `POST /api/tasks/{task_id}/override-priority`
- **Audit Parameters**: Accepts `override_score` ($0\text{--}100$), `override_reason` (mandatory textual justification), and `overridden_by` (controller identifier).
- **Audit Trail**: Overrides are stored in the decision history, recording original score, new score, dispatcher identity, justification, and timestamp.
- **Frontend Modal**: Accessible directly from the task management view in the web dashboard.

---

## 12. Performance & Optimizations

The optimization pipeline incorporates several architectural optimizations:

1. **Eager-Loaded ORM Queries**: Eliminates N+1 query patterns during timetable and block loading using SQLAlchemy `selectinload` for related movements and tasks.
2. **Timetable Preprocessing & Caching**: Pre-filters and indexes station stops and train trajectories by corridor and direction, avoiding repeated chainage interpolation.
3. **Safety-Check Short-Circuiting**: Bounding-box spatial filters quickly bypass train path envelope checks for non-overlapping track sections.
4. **Batched Persistence**: Registers all planned blocks, block-task associations, and schedule decisions in a single transactional batch, avoiding per-record database round-trips.

### Measured Benchmark Summary (30-Day Planning Horizon, 420 Tasks)

| Corridor | Tasks Evaluated | Tasks Scheduled | Planned Blocks | Solver Time | Backend Time | API Wall-Clock Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SBC-JTJ** (145 km) | 420 | 395 | 131 | ~16.3s | ~17.8s | ~18.2s |
| **NDLS-CNB** (440 km) | 420 | 408 | 151 | ~12.0s | ~13.8s | ~15.5s |
| **CSTM-PUNE** (192 km) | 420 | 403 | 86 | ~12.5s | ~14.4s | ~20.3s |

*Note: Solver time represents internal CP-SAT search time. Backend time includes data retrieval and serialization. Wall-clock time includes HTTP transport. Performance may vary based on database network latency and server hardware.*

---

## 13. Automated Test Suite

RailVyuha maintains comprehensive automated test coverage across unit, integration, and regression suites:

```bash
python -m pytest backend/tests/ -v
```

### Test Coverage Areas (56 Tests Passing)
- **Multi-Corridor Isolation** (`test_corridor_isolation.py`): Verifies chainage boundaries, asset ownership, timetable partitioning, solver isolation, and spatial location queries across all three corridors.
- **Optimizer & Safety Regressions** (`test_optimizer.py`): Validates task grouping, deadline enforcement, priority-based scheduling, 48 km unsafe cluster splitting, 20 km transitive graph partition compliance, and timetable interpolation correctness.
- **Freight & Headway Models** (`test_freight_model.py`): Tests freight uncertainty envelopes, safety buffers, and directional separation.
- **Database & Persistence** (`test_database.py`): Validates relational integrity, foreign keys, batched persistence units of work, and transaction rollback semantics.
- **Machine Learning Pipeline** (`test_ml_pipeline.py`): Tests feature extraction, temporal observation window leakage prevention, small-sample bootstrap fallback, model serialization, and explainability scoring.
- **API Endpoints & Lifecycle** (`test_api.py`): Tests task defaults, priority previewing, lifecycle transitions, dispatcher priority overrides, and decision lookups.
- **Frontend Production Build**: Verified with Vite (`npm run build` in `frontend/`, 0 errors).

---

## 14. Current Limitations

1. **Synthetic Workload Data**: Maintenance work orders, asset registries, historical maintenance logs, and freight forecasts are synthetically generated for demonstration and development purposes.
2. **ML Generalizability**: The recurrence risk model has been trained on synthetic calibration data and has not been validated on real-world Indian Railways defect histories.
3. **No Direct Production System Interface**: RailVyuha does not interface directly with live Indian Railways production systems (e.g., COA, FOIS, TMS, ICMS).
4. **Timetable Scope**: Passenger schedules are derived from the publicly available Datameet dataset and may not reflect temporary diversions, speed restrictions, or dynamic timetable changes.
5. **Operational Prerequisites**: Deployment in active railway operations would require domain validation, safety case certifications, and integration with railway communication protocols.

---

## 15. Setup & Running Instructions

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18 or higher (with npm)
- **PostgreSQL**: 15+ with PostGIS extension (local or cloud-hosted, e.g., Supabase, Neon, AWS RDS)

### 1. Environment Configuration

Copy the example environment configuration:
```bash
cp backend/.env.example backend/.env
```

Configure your connection string in `backend/.env`:
```ini
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/railvyuha
APP_ENV=development
LOG_LEVEL=INFO
DEFAULT_CORRIDOR_CODE=SBC-JTJ
```

*(Connection strings with `postgres://` or `postgresql://` prefixes are automatically normalized to the `postgresql+psycopg` driver).*

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Database Migration & Seeding

Apply Alembic migrations to create the database schema:
```bash
cd backend
alembic upgrade head
```

Seed corridors, stations, timetables, synthetic assets, history, and maintenance requests:
```bash
# Seeds all supported corridors (SBC-JTJ, NDLS-CNB, CSTM-PUNE)
python seed.py
```

### 4. Train & Persist the ML Model Artifact

Train the recurrence prediction model and generate serialization artifacts:
```bash
python train.py
```

### 5. Run the Backend API Server

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base: `http://127.0.0.1:8000`
- Interactive Swagger Documentation: `http://127.0.0.1:8000/docs`

### 6. Install & Run the Frontend Dashboard

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
- Dashboard URL: `http://localhost:3000`

### 7. Run Automated Tests

```bash
# Run all backend unit, integration, and regression tests
python -m pytest backend/tests/ -v

# Run frontend production build validation
cd frontend
npm run build
```

---

## 16. Repository Structure

```
RailSync/
├── backend/
│   ├── alembic/                      # Database migrations
│   │   └── versions/                 # Migration scripts
│   ├── alembic.ini                   # Alembic configuration
│   ├── artifacts/                    # Serialized models and metadata (git-ignored)
│   ├── core/
│   │   └── schemas.py                # Pydantic data schemas & API models
│   ├── db/
│   │   ├── base.py                   # SQLAlchemy Base and mixins
│   │   ├── models/                   # Relational ORM entity definitions
│   │   │   ├── assets.py             # Corridors, sections, stations, assets
│   │   │   ├── maintenance.py        # Requests, history, ML predictions, priorities
│   │   │   ├── operations.py         # Trains, runs, movements, freight forecasts
│   │   │   └── optimization.py       # Optimization runs, blocks, tasks, decisions
│   │   └── session.py                # Database engine & session management
│   ├── services/
│   │   ├── ai_prioritizer.py         # Explainable priority scoring engine
│   │   ├── compatibility.py          # Inter-departmental task compatibility rules
│   │   ├── ml_engine.py              # ML inference & feature extraction
│   │   ├── ml_training_pipeline.py   # ML training, cross-validation & evaluation
│   │   ├── mock_data.py              # Synthetic workload and freight generator
│   │   ├── optimizer.py              # CP-SAT scheduler & block consolidation
│   │   ├── real_corridor.py          # Datameet station & schedule loaders
│   │   ├── seeder.py                 # Idempotent corridor database seeder
│   │   └── timetable_analyzer.py     # Timetable occupancy & headway analyzer
│   ├── tests/                        # Automated pytest suite (56 tests)
│   │   ├── conftest.py               # Shared test fixtures & database rollback setup
│   │   ├── test_api.py               # API endpoint tests
│   │   ├── test_corridor_isolation.py# Multi-corridor isolation tests
│   │   ├── test_database.py          # Relational schema & persistence tests
│   │   ├── test_freight_model.py     # Freight uncertainty & safety buffer tests
│   │   ├── test_lifecycle.py         # Work order lifecycle state tests
│   │   ├── test_location_and_department.py # KM radius & department query tests
│   │   ├── test_ml_pipeline.py       # Feature leakage & ML model tests
│   │   └── test_optimizer.py         # CP-SAT & block span regression tests
│   ├── main.py                       # FastAPI application & route handlers
│   ├── requirements.txt              # Python package dependencies
│   ├── seed.py                       # Database seeding entrypoint
│   └── train.py                      # ML training entrypoint
├── frontend/
│   ├── src/
│   │   ├── components/               # React UI components
│   │   │   ├── AnalyticsDashboard.jsx# Decision intelligence analytics
│   │   │   ├── BlockPlan.jsx         # Planned block inspector & action cards
│   │   │   ├── ControlRoom.jsx       # Interactive time-distance string chart
│   │   │   ├── Dashboard.jsx         # Main layout & corridor selector
│   │   │   ├── LocationQueryModal.jsx# KM radius query inspector
│   │   │   ├── OutcomeLoggingModal.jsx# Maintenance outcome feedback modal
│   │   │   ├── PriorityExplanationModal.jsx # Explainable priority factor breakdown
│   │   │   ├── PriorityOverrideModal.jsx    # Dispatcher priority override modal
│   │   │   └── TaskTable.jsx         # Maintenance work order registry
│   │   ├── services/
│   │   │   └── api.js                # Frontend API client
│   │   ├── App.jsx                   # Application root
│   │   └── main.jsx                  # React entrypoint
│   ├── package.json                  # Frontend dependencies and scripts
│   └── vite.config.js                # Vite build configuration
├── .gitignore                        # Git exclusion rules
└── README.md                         # Project documentation
```
