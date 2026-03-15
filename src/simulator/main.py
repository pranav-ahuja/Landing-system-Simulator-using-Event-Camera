import argparse
import math
import time
from dataclasses import dataclass

import airsim
import msgpackrpc
import numpy as np


@dataclass
class Waypoint:
    x: float
    y: float
    z: float
    speed: float = 3.0


class AirSimDroneSimulator:
    def __init__(self, ip: str = "127.0.0.1", vehicle_name: str = "Drone1") -> None:
        self.ip = ip
        self.vehicle_name = vehicle_name
        self.client = airsim.MultirotorClient(ip=ip)

    def connect(self) -> None:
        self.client.confirmConnection()
        self.client.enableApiControl(True, vehicle_name=self.vehicle_name)
        self.client.armDisarm(True, vehicle_name=self.vehicle_name)

    def disconnect(self) -> None:
        self.client.armDisarm(False, vehicle_name=self.vehicle_name)
        self.client.enableApiControl(False, vehicle_name=self.vehicle_name)

    def takeoff(self, altitude: float = -5.0) -> None:
        self.client.takeoffAsync(vehicle_name=self.vehicle_name).join()
        self.client.moveToZAsync(altitude, 2, vehicle_name=self.vehicle_name).join()

    def land(self) -> None:
        self.client.landAsync(vehicle_name=self.vehicle_name).join()

    def fly_waypoints(self, waypoints: list[Waypoint]) -> None:
        for wp in waypoints:
            self.client.moveToPositionAsync(
                wp.x,
                wp.y,
                wp.z,
                wp.speed,
                drivetrain=airsim.DrivetrainType.MaxDegreeOfFreedom,
                yaw_mode=airsim.YawMode(is_rate=False, yaw_or_rate=0),
                vehicle_name=self.vehicle_name,
            ).join()

    def capture_rgb(self, filename: str = "front_rgb.png") -> None:
        responses = self.client.simGetImages(
            [airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)],
            vehicle_name=self.vehicle_name,
        )

        if not responses:
            raise RuntimeError("No image response received from AirSim.")

        image = responses[0]
        img_1d = np.frombuffer(image.image_data_uint8, dtype=np.uint8)
        img_rgb = img_1d.reshape(image.height, image.width, 3)
        airsim.write_png(filename, img_rgb)


def build_square_mission(size: float = 15.0, altitude: float = -5.0) -> list[Waypoint]:
    return [
        Waypoint(0, 0, altitude),
        Waypoint(size, 0, altitude),
        Waypoint(size, size, altitude),
        Waypoint(0, size, altitude),
        Waypoint(0, 0, altitude),
    ]


def yaw_spin(sim: AirSimDroneSimulator, total_rotation_deg: float = 360.0) -> None:
    state = sim.client.getMultirotorState(vehicle_name=sim.vehicle_name)
    quat = state.kinematics_estimated.orientation
    yaw_now = math.degrees(airsim.to_eularian_angles(quat)[2])
    sim.client.rotateToYawAsync(yaw_now + total_rotation_deg, 25, vehicle_name=sim.vehicle_name).join()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AirSim drone simulator mission runner")
    parser.add_argument("--ip", default="127.0.0.1", help="AirSim server IP")
    parser.add_argument("--vehicle", default="Drone1", help="Vehicle name in AirSim settings")
    parser.add_argument("--size", type=float, default=15.0, help="Square path side length (meters)")
    parser.add_argument("--altitude", type=float, default=-5.0, help="Cruise altitude in NED frame")
    parser.add_argument("--capture", action="store_true", help="Capture an RGB image after mission")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sim = AirSimDroneSimulator(ip=args.ip, vehicle_name=args.vehicle)
    connected = False

    try:
        sim.connect()
        connected = True
        sim.takeoff(altitude=args.altitude)
        mission = build_square_mission(size=args.size, altitude=args.altitude)
        sim.fly_waypoints(mission)
        yaw_spin(sim)

        if args.capture:
            stamp = int(time.time())
            sim.capture_rgb(filename=f"mission_capture_{stamp}.png")

        sim.land()
    except msgpackrpc.error.TransportError as exc:
        raise SystemExit(
            "Could not connect to AirSim RPC server at "
            f"{args.ip}:41451. Ensure an AirSim environment is running. "
            f"Details: {exc}"
        )
    finally:
        if connected:
            sim.disconnect()


if __name__ == "__main__":
    main()
