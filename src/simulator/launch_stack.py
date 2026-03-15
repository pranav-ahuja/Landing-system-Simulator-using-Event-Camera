import argparse
import socket
import time
from dataclasses import dataclass

import airsim
import msgpackrpc


@dataclass
class HealthCheckResult:
    name: str
    ok: bool
    details: str


@dataclass
class PhaseAConfig:
    airsim_ip: str
    vehicle: str
    sitl_endpoint: str
    attempts: int
    retry_delay_s: float
    prepare_api_control: bool


def parse_host_port(endpoint: str) -> tuple[str, int]:
    if ":" not in endpoint:
        raise ValueError(f"Endpoint '{endpoint}' must be in host:port format.")

    host, raw_port = endpoint.rsplit(":", 1)
    if not host:
        raise ValueError("Endpoint host cannot be empty.")

    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError(f"Port '{raw_port}' is not an integer.") from exc

    if not (1 <= port <= 65535):
        raise ValueError("Port must be between 1 and 65535.")

    return host, port


def check_sitl_endpoint(endpoint: str) -> HealthCheckResult:
    try:
        host, port = parse_host_port(endpoint)
        socket.getaddrinfo(host, port)
    except Exception as exc:  # noqa: BLE001 - expose full detail to operator
        return HealthCheckResult(
            name="SITL endpoint config",
            ok=False,
            details=f"Invalid endpoint '{endpoint}': {exc}",
        )

    return HealthCheckResult(
        name="SITL endpoint config",
        ok=True,
        details=f"Using MAVLink endpoint udp:{host}:{port}",
    )


def check_airsim_connectivity(ip: str, attempts: int, retry_delay_s: float) -> tuple[HealthCheckResult, airsim.MultirotorClient | None]:
    last_error = ""

    for attempt in range(1, attempts + 1):
        client = airsim.MultirotorClient(ip=ip)
        try:
            client.confirmConnection()
            return (
                HealthCheckResult(
                    name="AirSim RPC",
                    ok=True,
                    details=f"Connected to {ip}:41451 on attempt {attempt}/{attempts}",
                ),
                client,
            )
        except msgpackrpc.error.TransportError as exc:
            last_error = str(exc)
            if attempt < attempts:
                time.sleep(retry_delay_s)

    return (
        HealthCheckResult(
            name="AirSim RPC",
            ok=False,
            details=(
                f"Failed to connect to {ip}:41451 after {attempts} attempts. "
                f"Last error: {last_error}"
            ),
        ),
        None,
    )


def check_vehicle(client: airsim.MultirotorClient, vehicle: str) -> HealthCheckResult:
    try:
        state = client.getMultirotorState(vehicle_name=vehicle)
    except msgpackrpc.error.RPCError as exc:
        available = []
        try:
            if hasattr(client, "listVehicles"):
                available = client.listVehicles()
        except Exception:
            available = []

        details = [f"Could not read state for vehicle '{vehicle}'", f"RPC details: {exc}"]
        if available:
            details.append(f"Available vehicles: {', '.join(available)}")

        return HealthCheckResult(name="Vehicle availability", ok=False, details="; ".join(details))

    position = state.kinematics_estimated.position
    return HealthCheckResult(
        name="Vehicle availability",
        ok=True,
        details=f"Vehicle '{vehicle}' state OK at ({position.x_val:.2f}, {position.y_val:.2f}, {position.z_val:.2f})",
    )


def check_api_control(client: airsim.MultirotorClient, vehicle: str, prepare: bool) -> HealthCheckResult:
    if not prepare:
        return HealthCheckResult(
            name="API control prep",
            ok=True,
            details="Skipped (--no-prepare-api-control).",
        )

    try:
        client.enableApiControl(True, vehicle_name=vehicle)
        armed = client.armDisarm(True, vehicle_name=vehicle)
        client.armDisarm(False, vehicle_name=vehicle)
        client.enableApiControl(False, vehicle_name=vehicle)
    except msgpackrpc.error.RPCError as exc:
        return HealthCheckResult(
            name="API control prep",
            ok=False,
            details=f"Could not toggle API control/arm state for '{vehicle}': {exc}",
        )

    return HealthCheckResult(
        name="API control prep",
        ok=True,
        details=f"API control toggled successfully for '{vehicle}' (arm capability={armed}).",
    )


def print_summary(results: list[HealthCheckResult]) -> None:
    print("\n=== Phase A health-check summary ===")
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.details}")

    passed = sum(1 for r in results if r.ok)
    print(f"\nResult: {passed}/{len(results)} checks passed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase A platform stabilization checks for AirSim + SITL pipeline"
    )
    parser.add_argument("--airsim-ip", default="127.0.0.1", help="AirSim RPC IP")
    parser.add_argument("--vehicle", default="Drone1", help="AirSim vehicle name")
    parser.add_argument(
        "--sitl-endpoint",
        default="127.0.0.1:14550",
        help="Target MAVLink endpoint in host:port form",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=5,
        help="AirSim connection attempts (Phase A exit target is 5/5)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=1.0,
        help="Delay (s) between AirSim connection retries",
    )
    parser.add_argument(
        "--no-prepare-api-control",
        action="store_true",
        help="Skip API control and arm/disarm toggling check",
    )
    return parser.parse_args()


def run_phase_a_checks(cfg: PhaseAConfig) -> int:
    results: list[HealthCheckResult] = []

    sitl_result = check_sitl_endpoint(cfg.sitl_endpoint)
    results.append(sitl_result)

    airsim_result, client = check_airsim_connectivity(
        ip=cfg.airsim_ip,
        attempts=cfg.attempts,
        retry_delay_s=cfg.retry_delay_s,
    )
    results.append(airsim_result)

    if client is not None:
        vehicle_result = check_vehicle(client=client, vehicle=cfg.vehicle)
        results.append(vehicle_result)

        api_result = check_api_control(
            client=client,
            vehicle=cfg.vehicle,
            prepare=cfg.prepare_api_control,
        )
        results.append(api_result)

    print_summary(results)
    return 0 if all(result.ok for result in results) else 1


def main() -> None:
    args = parse_args()

    cfg = PhaseAConfig(
        airsim_ip=args.airsim_ip,
        vehicle=args.vehicle,
        sitl_endpoint=args.sitl_endpoint,
        attempts=args.attempts,
        retry_delay_s=args.retry_delay,
        prepare_api_control=not args.no_prepare_api_control,
    )

    raise SystemExit(run_phase_a_checks(cfg))


if __name__ == "__main__":
    main()
