# AirSim Drone Simulator (Linux)

This workspace contains a ready-to-run AirSim multirotor simulator client.

## What is included

- `src/simulator/main.py`: runs an autonomous square mission with takeoff, waypoint flight, yaw spin, and landing.
- `src/simulator/check_connection.py`: verifies client connection and prints drone position.
- `settings/settings.json`: AirSim configuration for one drone named `Drone1`.
- `scripts/run_mission.sh`: convenience launcher.

## 1) Install prerequisites

1. Use Python 3.10+.
2. Install project dependencies:

```bash
pip install -r requirements.txt
```

## 2) Start an AirSim environment

You can use the prebuilt **Blocks** environment from AirSim releases, or your own Unreal project with AirSim plugin.

Create a dedicated settings location (any name is fine):

```bash
mkdir -p ~/Documents/AirSim_MTech_Proj
cp settings/settings.json ~/Documents/AirSim_MTech_Proj/settings.json
```

Then start your AirSim environment and point it to that file if supported:

```bash
# Example launcher command (environment-specific)
./YourEnv.sh -settings ~/Documents/AirSim_MTech_Proj/settings.json
```

If you already have AirSimNH at `/home/pranav-ahuja/Documents/all_ws/AirSimNH`, use:

```bash
/home/pranav-ahuja/Documents/all_ws/AirSimNH/LinuxNoEditor/AirSimNH.sh -settings ~/Documents/AirSim_MTech_Proj/settings.json
```

If you use Unreal Editor, open your AirSim-enabled project and press Play.

## 3) Validate connection

From the project root:

```bash
PYTHONPATH=src python -m simulator.check_connection --ip 127.0.0.1 --vehicle Drone1
```

## 4) Run the mission

```bash
./scripts/run_mission.sh --ip 127.0.0.1 --vehicle Drone1 --size 20 --altitude -8
```

> Do not pass `-settings` to `run_mission.sh`. That flag belongs to the simulator environment launcher, not the Python mission client.

Optional direct run:

```bash
PYTHONPATH=src python -m simulator.main --capture
```

## Mission behavior

1. Connects to AirSim API.
2. Arms and takes off.
3. Flies a square trajectory.
4. Rotates yaw by 360°.
5. Optionally captures an RGB image.
6. Lands and disarms.

## Common issues

- **`Import "airsim" could not be resolved`** in editor:
  - Ensure the same interpreter is used where `pip install -r requirements.txt` was run.
- **Connection timeout**:
  - Check that the AirSim environment is running.
  - Verify `--ip` and firewall/network settings.
- **Vehicle not found**:
  - Ensure vehicle name matches `Drone1` in `settings.json` or pass `--vehicle`.
- **`getMultirotorState` RPC exception**:
  - AirSim RPC is reachable, but simulator is not in multirotor mode for that vehicle.
  - At AirSim startup prompt, choose **No** for car simulation (to use quadrotor).
  - Verify `--vehicle` matches the spawned multirotor name from settings.
