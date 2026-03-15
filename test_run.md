# Test Run Commands

## Common setup (every session)

```bash
source /home/pranav-ahuja/venv-ardupilot/bin/activate
cd /home/pranav-ahuja/Documents/all_ws/MTech_Proj/sim
```

## Start simulator (Terminal A)

```bash
/home/pranav-ahuja/Documents/all_ws/AirSimNH/LinuxNoEditor/AirSimNH.sh -settings /home/pranav-ahuja/Documents/AirSim_MTech_Proj/settings.json
```

## Phase A — platform stabilization (Terminal B)

```bash
source /home/pranav-ahuja/venv-ardupilot/bin/activate
cd /home/pranav-ahuja/Documents/all_ws/MTech_Proj/sim

for i in {1..5}; do
	echo "RUN $i"
	PYTHONPATH=src python -m simulator.check_connection --ip 127.0.0.1 --vehicle SimpleFlight || break
done
```

Optional port/process checks:

```bash
ss -ltn | grep 41451
pgrep -af AirSimNH
```

## Phase B — event pipeline baseline (once implemented)

```bash
PYTHONPATH=src python -m simulator.cli run --profile baseline_night --duration 120 --save-events --save-frames
```

## Phase C — scene/pad modeling (once implemented)

```bash
PYTHONPATH=src python -m simulator.cli run --profile pad_square_seed42 --duration 60
PYTHONPATH=src python -m simulator.cli run --profile pad_hex_seed42 --duration 60
PYTHONPATH=src python -m simulator.cli run --profile pad_h_seed42 --duration 60
```

Determinism replay:

```bash
PYTHONPATH=src python -m simulator.cli run --profile pad_square_seed42 --duration 60
```

## Phase D — SITL + LANDING_TARGET bridge (once implemented)

```bash
PYTHONPATH=src python -m simulator.cli check --s-itl 127.0.0.1:14550 --airsim 127.0.0.1
PYTHONPATH=src python -m simulator.cli run --profile sitl_bridge_test --duration 180
```

## Phase E — closed-loop landing trials (once implemented)

```bash
PYTHONPATH=src python -m simulator.cli batch --profile closed_loop_night --trials 20 --seed 123
```

## Phase F — robustness campaign/report (once implemented)

```bash
PYTHONPATH=src python -m simulator.cli batch --profile robustness_matrix --trials 100 --seed 999
PYTHONPATH=src python -m simulator.cli analyze --input runs/robustness_matrix --report out/final_report.md
```

## Current mission smoke test (already available now)

```bash
./scripts/run_mission.sh --ip 127.0.0.1 --vehicle SimpleFlight --size 20 --altitude -8 --capture
```
