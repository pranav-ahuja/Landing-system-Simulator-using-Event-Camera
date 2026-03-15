# Test Run Commands
## Activate Airsim
- `source /home/pranav-ahuja/venv-ardupilot/bin/activate
/home/pranav-ahuja/Documents/all_ws/AirSimNH/LinuxNoEditor/AirSimNH.sh -settings ~/Documents/AirSim_MTech_Proj/settings.json`

## Test Connection
- `source /home/pranav-ahuja/venv-ardupilot/bin/activate
cd /home/pranav-ahuja/Documents/all_ws/MTech_Proj/sim
PYTHONPATH=src python -m simulator.check_connection --ip 127.0.0.1 --vehicle SimpleFlight`

## Run Implementation
### Implementation A
- `source /home/pranav-ahuja/venv-ardupilot/bin/activate
cd /home/pranav-ahuja/Documents/all_ws/MTech_Proj/sim
./scripts/run_phase_a_checks.sh --airsim-ip 127.0.0.1 --vehicle SimpleFlight --sitl-endpoint 127.0.0.1:14550`
