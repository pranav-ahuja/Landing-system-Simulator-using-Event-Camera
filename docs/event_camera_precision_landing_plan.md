# Event-Camera Precision Landing (AirSim + ArduPilot SITL) — Planning Document

## Table of Contents

- [Event-Camera Precision Landing (AirSim + ArduPilot SITL) — Planning Document](#event-camera-precision-landing-airsim--ardupilot-sitl--planning-document)
  - [Table of Contents](#table-of-contents)
  - [1) Goal](#1-goal)
  - [2) Problem Context (as provided)](#2-problem-context-as-provided)
  - [3) What AirSim gives us for event-camera simulation](#3-what-airsim-gives-us-for-event-camera-simulation)
  - [4) Target Simulation Architecture](#4-target-simulation-architecture)
  - [4.1 Logical data path](#41-logical-data-path)
  - [4.2 Suggested process split (simulation-only)](#42-suggested-process-split-simulation-only)
  - [5) Scenario \& World Modeling Plan](#5-scenario--world-modeling-plan)
  - [5.1 Landing pad digital twin](#51-landing-pad-digital-twin)
  - [5.2 IR emitter representation in AirSim/Unreal](#52-ir-emitter-representation-in-airsimunreal)
  - [5.3 Environment variation set](#53-environment-variation-set)
  - [6) Event Simulation Strategy](#6-event-simulation-strategy)
  - [6.1 Phase-1 strategy (recommended)](#61-phase-1-strategy-recommended)
  - [6.2 Phase-2 strategy (higher fidelity)](#62-phase-2-strategy-higher-fidelity)
  - [6.3 Required simulator outputs](#63-required-simulator-outputs)
  - [7) FCU Integration Plan (ArduPilot SITL)](#7-fcu-integration-plan-ardupilot-sitl)
  - [7.1 Message path](#71-message-path)
  - [7.2 FCU-side expectations](#72-fcu-side-expectations)
  - [7.3 Control-loop checks](#73-control-loop-checks)
  - [8) Validation Plan](#8-validation-plan)
  - [8.1 KPIs (must be measured)](#81-kpis-must-be-measured)
  - [8.2 Test matrix](#82-test-matrix)
  - [8.3 Ground-truth comparison](#83-ground-truth-comparison)
  - [9) Milestone Plan (No coding yet)](#9-milestone-plan-no-coding-yet)
  - [M0 — Baseline connectivity (done/near-done)](#m0--baseline-connectivity-donenear-done)
  - [M1 — Event-sim data path](#m1--event-sim-data-path)
  - [M2 — Landing pad scene variants](#m2--landing-pad-scene-variants)
  - [M3 — Perception stub + MAVLink plumbing](#m3--perception-stub--mavlink-plumbing)
  - [M4 — Closed-loop precision landing in sim](#m4--closed-loop-precision-landing-in-sim)
  - [M5 — Robustness campaign](#m5--robustness-campaign)
  - [10) Risks and Mitigations](#10-risks-and-mitigations)
  - [11) Deliverables](#11-deliverables)
  - [12) Recommended Immediate Next Step (after planning approval)](#12-recommended-immediate-next-step-after-planning-approval)
  - [13) What will be coded for this project](#13-what-will-be-coded-for-this-project)
  - [13.1 Simulator orchestration](#131-simulator-orchestration)
  - [13.2 AirSim camera capture and synchronization](#132-airsim-camera-capture-and-synchronization)
  - [13.3 Event camera simulation layer](#133-event-camera-simulation-layer)
  - [13.4 Landing pad and scenario manager](#134-landing-pad-and-scenario-manager)
  - [13.5 Perception interface (Jetson-equivalent placeholder)](#135-perception-interface-jetson-equivalent-placeholder)
  - [13.6 MAVLink `LANDING_TARGET` bridge](#136-mavlink-landing_target-bridge)
  - [13.7 Evaluation and reporting](#137-evaluation-and-reporting)
  - [13.8 CLI tools and scripts](#138-cli-tools-and-scripts)
  - [13.9 Tests](#139-tests)
  - [13.10 What is explicitly not coded yet](#1310-what-is-explicitly-not-coded-yet)
  - [14) Phased Development Breakdown](#14-phased-development-breakdown)
  - [14.1 Phase A — Platform stabilization](#141-phase-a--platform-stabilization)
  - [14.2 Phase B — Event pipeline baseline](#142-phase-b--event-pipeline-baseline)
  - [14.3 Phase C — Scene and pad modeling](#143-phase-c--scene-and-pad-modeling)
  - [14.4 Phase D — SITL control integration](#144-phase-d--sitl-control-integration)
  - [14.5 Phase E — Closed-loop landing trials](#145-phase-e--closed-loop-landing-trials)
  - [14.6 Phase F — Robustness and reporting](#146-phase-f--robustness-and-reporting)
  - [14.7 Exit criteria for hardware transition](#147-exit-criteria-for-hardware-transition)

## 1) Goal

Build a **simulation-first validation stack** for night-time precision landing using an event-camera pipeline, before hardware deployment on:

- FCU (ArduPilot)
- Companion computer (Jetson equivalent in sim)
- Event camera (simulated)

The simulator should prove that the landing concept works when GPS and AprilTag are weak or unavailable (night, dust/snow coverage, terrain uncertainty).

---

## 2) Problem Context (as provided)

- GPS-only landing is not precise enough in challenging terrain.
- AprilTag is fragile in low-light/night and when marker visibility is degraded (snow/sand occlusion).
- Proposed landing pad uses IR emitters with:
  - geometric structure (square / hexagon / polygon / “H”),
  - corner and edge emitters,
  - independent blinking frequencies (including >1 kHz target behavior).

System concept:

1. Drone flies near target area via GPS.
2. Event stream is processed on Jetson.
3. Jetson sends `LANDING_TARGET` MAVLink messages to FCU.
4. FCU executes precision landing behavior.

---

## 3) What AirSim gives us for event-camera simulation

From AirSim documentation (`event_sim`):

- AirSim includes a **Python event simulator** that converts consecutive RGB frames to events.
- Event format: `<x> <y> <timestamp> <polarity>`.
- Provides event image accumulation for visualization.
- Core controls include resolution and event threshold (`TOL`), plus event count limits.

Important implication:

- This event stream is synthesized from rendered frames; temporal fidelity depends on simulator frame cadence and interpolation model.
- For very high-frequency LED behavior (e.g., >1 kHz), validation must distinguish:
  - **algorithmic feasibility** in synthetic data,
  - versus **physics-accurate sensor timing** (to be confirmed later in hardware tests).

---

## 4) Target Simulation Architecture

## 4.1 Logical data path

1. **AirSim + ArduPilot SITL** runs vehicle dynamics and camera rendering.
2. **Event-camera simulation node** consumes RGB/IR-like frames and outputs event packets.
3. **Landing perception node (Jetson-equivalent)** consumes event packets and estimates landing target pose/offset.
4. **MAVLink bridge node** sends `LANDING_TARGET` to ArduPilot SITL.
5. ArduPilot performs precision landing control.

## 4.2 Suggested process split (simulation-only)

- Process A: AirSimNH environment (Unreal packaged binary)
- Process B: ArduPilot SITL + MAVProxy (or equivalent)
- Process C: Event simulator + perception + MAVLink publisher (Python)
- Optional Process D: Recorder/metrics (logs, plots, replay)

---

## 5) Scenario & World Modeling Plan

## 5.1 Landing pad digital twin

Create multiple pad variants:

- Square
- Hexagon
- “H” pattern
- Custom polygon

Each variant should have parameterized:

- LED coordinates (3D positions)
- blinking frequencies / duty cycles / phase offsets
- intensity model (relative brightness)

## 5.2 IR emitter representation in AirSim/Unreal

Simulation representations (in increasing realism):

1. **Bright emissive materials only** (fast baseline)
2. **Emissive + point lights** for visibility stress tests
3. **Frequency-coded temporal modulation** per emitter

## 5.3 Environment variation set

- Night clear
- Fog/haze
- Rain/snow-like visibility degradation
- Dust/sand contrast reduction
- Partial occlusion of pad
- Different ground textures/background clutter

---

## 6) Event Simulation Strategy

## 6.1 Phase-1 strategy (recommended)

Use AirSim’s documented event simulation approach (RGB-frame-based) to quickly validate:

- detection/tracking pipeline,
- control loop wiring,
- MAVLink message flow,
- precision landing behavior.

## 6.2 Phase-2 strategy (higher fidelity)

Evaluate more realistic event synthesis for high-frequency beacon behavior:

- tune threshold/noise/refractory assumptions,
- compare response to known LED modulation frequencies,
- quantify where frame-derived event sim diverges from expected hardware behavior.

## 6.3 Required simulator outputs

- raw events (`x,y,t,pol`)
- event image (for debug)
- synchronized ground truth:
  - drone pose,
  - camera pose/intrinsics,
  - landing pad pose.

---

## 7) FCU Integration Plan (ArduPilot SITL)

## 7.1 Message path

- Perception node computes target relative pose/offset.
- MAVLink bridge sends `LANDING_TARGET` at controlled rate and timestamp discipline.

## 7.2 FCU-side expectations

- Precision landing parameters configured in SITL profile.
- Landing mode transitions and failsafes defined (loss of target, stale message, noisy target).

## 7.3 Control-loop checks

- Message rate, latency, jitter.
- Target-frame consistency (camera/body/NED conventions).
- Behavior when target is intermittent.

---

## 8) Validation Plan

## 8.1 KPIs (must be measured)

- Final landing error (cm)
- Touchdown success rate (%)
- Time-to-land (s)
- Target reacquisition time after occlusion (s)
- Robustness versus illumination and clutter
- End-to-end latency (event generation → `LANDING_TARGET` → FCU response)

## 8.2 Test matrix

Axes:

- altitude bands (high approach / mid / terminal)
- lateral initial offset
- wind/disturbance profile
- emitter pattern (square/hex/H)
- frequency plans and phase patterns
- weather/noise conditions

## 8.3 Ground-truth comparison

- Compare estimated target offsets against simulator truth.
- Build error histograms and percentile metrics ($P50$, $P90$, $P99$).

---

## 9) Milestone Plan (No coding yet)

## M0 — Baseline connectivity (done/near-done)

- AirSimNH running
- SITL integration path identified
- vehicle control script validated

## M1 — Event-sim data path

- Pull frames from AirSim camera
- Generate event stream + debug visualization
- Log synchronized timestamps

## M2 — Landing pad scene variants

- Add pad geometries + emitter layouts
- Add blink profile definitions
- Create repeatable scenario presets

## M3 — Perception stub + MAVLink plumbing

- Placeholder estimator (not full CV yet)
- send `LANDING_TARGET` to SITL
- verify FCU consumes messages correctly

## M4 — Closed-loop precision landing in sim

- autonomous descent using simulated target feed
- failsafe behavior validation

## M5 — Robustness campaign

- run test matrix
- generate KPI report and go/no-go recommendation for hardware phase

---

## 10) Risks and Mitigations

1. **Temporal realism gap for >1 kHz emitter behavior**
   - Mitigation: explicitly label results as software-in-loop realism tier; add dedicated high-fidelity validation later.

2. **Coordinate-frame mismatch** (`camera` ↔ `body` ↔ `NED`)
   - Mitigation: add frame-convention checklist and synthetic sanity tests.

3. **MAVLink timing drift / jitter**
   - Mitigation: rate limiting, timestamp checks, and watchdog metrics.

4. **Scene overfitting**
   - Mitigation: randomized pad textures, backgrounds, weather, and approach trajectories.

5. **Packaged AirSimNH constraints**
   - Mitigation: if asset-level control is limited, move to Unreal project-level customization and repack.

---

## 11) Deliverables

1. Architecture diagram (logical + process)
2. Scenario definition spec (pad geometry, emitter map, frequencies)
3. Event simulation configuration spec
4. SITL integration spec (`LANDING_TARGET` timing + frames)
5. KPI dashboard/report template
6. Test matrix and execution checklist

---

## 12) Recommended Immediate Next Step (after planning approval)

Start with **M1 + M2 in parallel**:

- M1 establishes event stream and logging pipeline.
- M2 establishes controlled landing-pad scenarios.

This gives a stable foundation before implementing the actual CV/math estimator.

---

## 13) What will be coded for this project

This section lists the concrete code modules planned for implementation.

## 13.1 Simulator orchestration

- `src/simulator/launch_stack.py`
   - start/check runtime components (AirSim endpoint, SITL endpoint, logging folders)
   - load scenario profile and run-time parameters
   - provide one-command experiment execution

- `src/simulator/config/*.yaml`
   - experiment config files (camera, event-sim, MAVLink rates, landing mode)
   - reusable presets for night/fog/snow/dust scenarios

## 13.2 AirSim camera capture and synchronization

- `src/simulator/io/airsim_frame_source.py`
   - fetch RGB/infrared/depth frames from AirSim APIs
   - read camera intrinsics/extrinsics and timestamps
   - publish synchronized frame packets to downstream pipeline

- `src/simulator/io/ground_truth_logger.py`
   - log drone pose, velocity, camera pose, and landing pad truth per frame
   - write CSV/Parquet logs for later KPI computation

## 13.3 Event camera simulation layer

- `src/simulator/eventcam/event_generator.py`
   - wrap AirSim event simulator callback behavior
   - expose tunables: `TOL`, max events per frame pair, resolution
   - output both raw events (`x,y,t,pol`) and event image

- `src/simulator/eventcam/noise_models.py`
   - optional synthetic noise/refractory controls for robustness studies
   - parameter sets for day/night and difficult weather conditions

## 13.4 Landing pad and scenario manager

- `src/simulator/scenario/pad_layouts.py`
   - define square/hex/H/polygon emitter geometry in world coordinates
   - parameterize LED IDs, blink frequencies, duty cycle, phase

- `src/simulator/scenario/domain_randomization.py`
   - randomize initial altitude, offset, yaw, weather, background texture
   - generate reproducible seeded trials

## 13.5 Perception interface (Jetson-equivalent placeholder)

- `src/simulator/perception/event_target_estimator_stub.py`
   - consume event packets
   - output target bearing/offset/size confidence (stub logic first)
   - define stable interface for later CV/math algorithm drop-in

- `src/simulator/perception/interfaces.py`
   - typed input/output contracts so estimator can be replaced without changing MAVLink layer

## 13.6 MAVLink `LANDING_TARGET` bridge

- `src/simulator/mavlink/landing_target_bridge.py`
   - convert estimator output to MAVLink `LANDING_TARGET`
   - enforce message rate, timestamping, and frame convention
   - send to ArduPilot SITL over UDP/serial equivalent endpoint

- `src/simulator/mavlink/frame_transforms.py`
   - camera frame ↔ body frame ↔ NED transforms
   - utilities and unit-tested conversion helpers

## 13.7 Evaluation and reporting

- `src/simulator/eval/kpi.py`
   - compute landing error, success rate, reacquisition time, latency metrics

- `src/simulator/eval/report.py`
   - aggregate runs and generate summary tables/plots
   - export markdown/CSV report for experiment batches

## 13.8 CLI tools and scripts

- `scripts/run_event_pipeline.sh`
   - run frame capture + event sim + MAVLink bridge in one command

- `scripts/run_scenario_batch.sh`
   - execute seeded batch experiments and collect metrics

- `src/simulator/cli.py`
   - subcommands such as `check`, `run`, `batch`, `analyze`

## 13.9 Tests

- `tests/test_frame_transforms.py`
- `tests/test_event_generator.py`
- `tests/test_landing_target_bridge.py`
- `tests/test_kpi_metrics.py`

Focus of tests:

- frame/sign convention correctness,
- timestamp monotonicity,
- message-rate guarantees,
- deterministic outputs for seeded simulations.

## 13.10 What is explicitly not coded yet

- final production-grade CV/math estimator for event-based target localization,
- hardware drivers and Jetson deployment packaging,
- real-flight calibration and hardware-in-loop validation.

These are later phases after simulation validation gates are passed.

---

## 14) Phased Development Breakdown

The milestones above are now grouped into execution phases with clear scope and exit criteria.

## 14.1 Phase A — Platform stabilization

**Objective:** Ensure reproducible baseline stack operation.

**Scope:**
- AirSimNH startup + custom settings loading
- vehicle control/connection sanity checks
- ArduPilot SITL endpoint preparation

**Primary outputs:**
- stable runbook for startup/shutdown
- environment health-check checklist

**Exit criteria:**
- reproducible connection across 5/5 startup attempts
- consistent vehicle naming and API control

**How to test at end of implementation:**
- Run platform health check 5 times from clean start.
- Verify AirSim RPC ping, vehicle discovery, API arm/disarm cycle.
- Verify SITL endpoint reachability and heartbeat logging.
- Pass condition: all checks pass in 5/5 attempts.

## 14.2 Phase B — Event pipeline baseline

**Objective:** Build event-data path from AirSim imagery to event stream.

**Scope:**
- frame capture module
- event generation callback integration
- raw event and event-image logging

**Primary outputs:**
- timestamped event logs (`x,y,t,pol`)
- debug visualization pipeline

**Exit criteria:**
- continuous event generation during flight
- synchronized frame/event logs with no timestamp regressions

**How to test at end of implementation:**
- Run a fixed 2-minute flight path.
- Record frame timestamps and event timestamps.
- Validate monotonic timestamps and non-empty event stream throughout run.
- Pass condition: zero timestamp regressions, zero dropped pipeline crashes, valid event logs saved.

## 14.3 Phase C — Scene and pad modeling

**Objective:** Introduce controlled landing-pad scenarios.

**Scope:**
- pad geometry library (square/hex/H/polygon)
- emitter map and blink profile definitions
- initial weather/background variation presets

**Primary outputs:**
- scenario config set (`.yaml` profiles)
- deterministic seeded scenario playback

**Exit criteria:**
- at least 3 pad types validated in simulation
- repeatable scenario reproduction from seed/config

**How to test at end of implementation:**
- Execute seeded scenarios for square, hex, and H pads.
- Re-run the same seeds and compare generated layout and emitter parameters.
- Validate weather/background preset loading for each scenario profile.
- Pass condition: scenario replay is deterministic for identical seed/config.

## 14.4 Phase D — SITL control integration

**Objective:** Connect perception output to FCU via MAVLink.

**Scope:**
- placeholder estimator output contract
- `LANDING_TARGET` publisher
- frame transform and timing validation

**Primary outputs:**
- SITL receives and logs `LANDING_TARGET`
- rate/latency dashboard for message health

**Exit criteria:**
- stable `LANDING_TARGET` stream at target rate
- verified coordinate-frame consistency tests passing

**How to test at end of implementation:**
- Replay estimator outputs into MAVLink bridge for 3 minutes.
- Check SITL logs for `LANDING_TARGET` receive rate, jitter, and field validity.
- Run transform unit tests for camera/body/NED conversions.
- Pass condition: configured rate maintained and all transform tests pass.

## 14.5 Phase E — Closed-loop landing trials

**Objective:** Demonstrate autonomous precision landing in-loop.

**Scope:**
- guided approach + terminal landing behavior
- target loss/reacquisition handling
- failsafe trigger checks

**Primary outputs:**
- closed-loop trial logs
- first-pass success-rate and landing-error metrics

**Exit criteria:**
- successful autonomous landings in baseline night scenario
- no unsafe control oscillation in terminal descent

**How to test at end of implementation:**
- Run at least 20 autonomous landing trials in baseline night scenario.
- Measure landing error and touchdown success/failure per trial.
- Inspect descent profiles for oscillation near touchdown.
- Pass condition: stable descent behavior and success rate meets agreed threshold.

## 14.6 Phase F — Robustness and reporting

**Objective:** Stress test and quantify readiness.

**Scope:**
- batch test execution across weather/offset/frequency variations
- KPI computation and percentile summaries
- comparative analysis across pad geometries

**Primary outputs:**
- final experiment report
- go/no-go recommendation for hardware stage

**Exit criteria:**
- KPI thresholds met for selected operating envelope
- documented failure modes + mitigation plan

**How to test at end of implementation:**
- Run full batch matrix across offsets/weather/frequency patterns.
- Compute KPI distributions ($P50$, $P90$, $P99$) and compare to thresholds.
- Generate final report with failure cases and mitigation recommendations.
- Pass condition: thresholds met in target envelope, with signed-off report.

## 14.7 Exit criteria for hardware transition

Move to hardware-in-loop / field testing only when:

1. Landing error and success-rate KPIs are stable across repeated seeds.
2. `LANDING_TARGET` timing, rate, and frame transforms are verified.
3. Target loss/recovery behavior is demonstrated under at least 3 adverse conditions.
4. Assumptions and known simulator-vs-hardware gaps are explicitly documented.
