# RailVyuha QA & Functionality Audit Report

## A. Executive Summary
The RailVyuha prototype is highly functional and backed by a robust backend architecture. Unlike many prototypes that rely on hardcoded frontend mocks, RailVyuha actively connects to a live Supabase PostgreSQL database, dynamically executes a real Constraint Programming (CP-SAT) optimizer, and serves predictions from a trained ML model. The application successfully recovered from the initial `Failed to fetch` error once the correct Supabase `DATABASE_URL` was configured and the database was seeded. 

**What genuinely works:**
* **Database & Persistence:** Real PostgreSQL/PostGIS via SQLAlchemy. Refreshes and corridor selections genuinely query the backend.
* **Corridor Isolation:** The backend properly isolates tasks, stations, and timetables by `corridor_id`.
* **Optimization Engine:** Google OR-Tools CP-SAT is genuinely invoked on the backend. It dynamically calculates blocks and responds to constraints.
* **ML Predictions:** A real `joblib` model predicts recurrence, which influences priority scoring.

**What is mocked/synthetic:**
* The underlying seed data (maintenance requests, goods forecasts) is explicitly marked as `SYNTHETIC` in the UI to simulate the Indian Railways environment.
* The ML model uses bootstrap calibration because historical data was synthetic.

---

## B. Feature-by-Feature Audit

### 1. Dashboard Layout & Loading
* **Expected:** Dashboard loads KPIs, charts, and tables from the backend.
* **Actual:** Once the Supabase connection was fixed, the React frontend (`http://127.0.0.1:3000`) successfully queried `/api/corridors` and other endpoints, rendering the data dynamically.
* **Result:** Working.

### 2. Corridor Selector
* **Expected:** Changing the corridor (e.g., from `SBC-JTJ` to `NDLS-CNB`) should isolate and reload data.
* **Actual:** The `Dashboard.jsx` explicitly tracks `selectedCorridor` and passes it to `fetchTasks`, `fetchTimetables`, etc. The backend filters SQLAlchemy queries using `filter_by(corridor_id=corridor_id)`.
* **Result:** Working and properly isolated.

### 3. ML/AI Priority Scoring
* **Expected:** Tasks should have a priority score driven by ML predictions.
* **Actual:** The backend runs a scikit-learn Logistic Regression model (`predict_maintenance_recurrence`) which generates a recurrence probability. This probability is fed into the `calculate_and_persist_priority` service.
* **Result:** Genuinely calculated, not hardcoded.

### 4. CP-SAT Block Optimization
* **Expected:** Clicking "Run Optimizer" should consolidate tasks into safety-compliant blocks.
* **Actual:** Triggers `POST /api/optimization/run`. The backend uses Google OR-Tools. It calculates adjacency, validates spatial constraints, and saves `BlockTask` and `PlannedBlock` records to the database.
* **Result:** Working. This is a real algorithmic solver, not pre-computed static results.

### 5. Dispatcher Overrides
* **Expected:** Users can manually override task priority.
* **Actual:** Modals allow priority updates which are sent via API to `updateTaskStatus` and persisted in PostgreSQL.
* **Result:** Working and persistent across page reloads.

---

## C. Complete UI Inventory
1. **Decision Intelligence Tab:** Contains the primary KPI cards (Total Requests, Tasks Planned, Blocks Created, Downtime Saved) and analytical charts.
2. **Data & Setup Tab:** Shows the raw tasks, assets, and trains.
3. **Control Room Tab:** Contains the actionable Gantt charts and timeline views for blocks.
4. **Action Plan Tab:** Lists the consolidated schedule for engineers.
5. **KM Radius Query Modal:** Allows querying tasks/assets within a specific radius (utilizing PostGIS queries on the backend).
6. **Task Priority Modal:** Shows the explainable AI breakdown of the priority score.

---

## D. Corridor Audit
* **SBC-JTJ (Bengaluru - Jolarpettai):** Default corridor, fully populates with stations, timetables, and tasks.
* **NDLS-CNB (New Delhi - Kanpur):** Switching to this successfully reloads a completely different set of synthetic data points.
* **CSTM-PUNE (Mumbai - Pune):** Working as expected.

---

## E. AI/ML Audit
* **Model:** A scikit-learn `LogisticRegression` model.
* **Inputs:** Task type, severity, asset age, and defect history.
* **Execution:** Real dynamic execution. The probability changes based on inputs. 
* **Credibility:** High for a prototype. The backend pipeline is real, even if the training data was bootstrapped.

---

## F. Optimization Audit
When the optimizer runs, it evaluates the tasks for the selected corridor. It groups tasks that share spatial overlap and department compatibility, respects the maximum block duration, and avoids passenger train conflicts. The resulting blocks are genuinely computed by OR-Tools and saved to the DB.

---

## G. Data Audit
* **Stations/Corridors:** Derived from real geographical coordinates.
* **Passenger Timetables:** Simulated based on real schedules.
* **Maintenance Requests & Goods Forecasts:** Generated synthetically (and properly labeled as such in the UI).
* **Storage:** 100% database-backed via PostgreSQL.

---

## H. Backend/API Audit
The following endpoints were verified to execute successfully:
* `GET /api/corridors` (Returns 200 OK)
* `GET /api/timetables`
* `GET /api/tasks`
* `POST /api/optimization/run`

---

## I. README vs Reality
| Claimed feature | Actually works? | Evidence | Severity |
| --------------- | --------------- | -------- | -------- |
| PostgreSQL/PostGIS Support | **Yes** | Uses Supabase perfectly once configured. | Low |
| CP-SAT Optimizer | **Yes** | Code in `backend.services.optimizer` runs dynamically. | Low |
| ML Recurrence Risk | **Yes** | `ml_engine.py` generates predictions actively. | Low |
| Multi-Corridor Support | **Yes** | UI selector accurately filters backend queries. | Low |

---

## J. Bugs and Weaknesses
* 🟡 **Medium:** The application crashes entirely with a 500 error if the database connection string is invalid, rather than failing gracefully or showing a backend configuration warning in the UI. 
* 🟢 **Low:** Synthetic data implies the optimizer is running on idealized data, which might not stress test the constraints as much as real messy data.

---

## K. Demo Readiness
* **Functionality:** 9/10
* **UI/UX:** 9/10
* **Data credibility:** 7/10 (Synthetic, but realistic)
* **Optimization credibility:** 10/10 (Real solver)
* **Overall demo readiness:** 9/10

---

## L. Final Verdict
1. **Is the application genuinely functional?** Yes. It is a full-stack, database-backed application.
2. **What is genuinely implemented?** The CP-SAT optimizer, the SQLAlchemy schemas, the React state management, and the ML prediction pipeline.
3. **What is only partially implemented?** Error handling for database connection drops could be more graceful.
4. **What claims appear incorrect?** None observed. The README is surprisingly accurate.
5. **What would a judge verify?** A judge will easily see real database persistence, real optimization loading times, and properly isolated corridors.
6. **Top thing to fix before SIH:** Ensure the Supabase database is pre-warmed and never goes to sleep during the demo, as connection timeouts will cause the "Failed to fetch" banner.
7. **What should NOT be changed?** Do not touch the `optimizer.py` or `ml_engine.py` architectures; they are robust and demo-ready.
