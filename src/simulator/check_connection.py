import argparse

import airsim
import msgpackrpc


def main() -> None:
    parser = argparse.ArgumentParser(description="Check AirSim connection")
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--vehicle", default="Drone1")
    args = parser.parse_args()

    client = airsim.MultirotorClient(ip=args.ip)
    try:
        client.confirmConnection()
    except msgpackrpc.error.TransportError as exc:
        raise SystemExit(
            "Could not connect to AirSim RPC server at "
            f"{args.ip}:41451. Ensure an AirSim environment is running. "
            f"Details: {exc}"
        )

    try:
        state = client.getMultirotorState(vehicle_name=args.vehicle)
    except msgpackrpc.error.RPCError as exc:
        available = []
        try:
            if hasattr(client, "listVehicles"):
                available = client.listVehicles()
        except Exception:
            available = []

        details = [
            "Connected to AirSim RPC server, but could not read multirotor state.",
            f"Vehicle requested: {args.vehicle}",
            "This usually means one of the following:",
            "1) The sim is running in Car mode instead of Multirotor mode.",
            "2) Vehicle name does not match your settings JSON.",
            "3) No multirotor vehicle is spawned yet.",
        ]

        if available:
            details.append(f"Vehicles currently reported by AirSim: {', '.join(available)}")

        details.append(f"RPC details: {exc}")
        raise SystemExit("\n".join(details))

    pos = state.kinematics_estimated.position
    print(f"Connected to AirSim. Vehicle={args.vehicle}, position=({pos.x_val:.2f}, {pos.y_val:.2f}, {pos.z_val:.2f})")


if __name__ == "__main__":
    main()
