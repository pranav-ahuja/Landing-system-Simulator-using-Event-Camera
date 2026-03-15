from __future__ import annotations

from dataclasses import dataclass

import airsim
import numpy as np


@dataclass
class FramePacket:
    timestamp_us: int
    image_rgb: np.ndarray
    camera_position: tuple[float, float, float]
    camera_orientation: tuple[float, float, float, float]


class AirSimFrameSource:
    def __init__(self, ip: str, vehicle_name: str, camera_name: str = "0") -> None:
        self.ip = ip
        self.vehicle_name = vehicle_name
        self.camera_name = camera_name
        self.client = airsim.MultirotorClient(ip=ip)

    def connect(self) -> None:
        self.client.confirmConnection()

    def capture(self) -> FramePacket:
        responses = self.client.simGetImages(
            [airsim.ImageRequest(self.camera_name, airsim.ImageType.Scene, False, False)],
            vehicle_name=self.vehicle_name,
        )
        if not responses:
            raise RuntimeError("No image response from AirSim")

        response = responses[0]
        if response.width <= 0 or response.height <= 0:
            raise RuntimeError("Invalid frame shape from AirSim")

        img_1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)
        img_rgb = img_1d.reshape(response.height, response.width, 3)
        img_rgb = np.flipud(img_rgb)

        ts_us = int(response.time_stamp // 1_000) if response.time_stamp else 0

        pos = response.camera_position
        ori = response.camera_orientation

        return FramePacket(
            timestamp_us=ts_us,
            image_rgb=img_rgb,
            camera_position=(pos.x_val, pos.y_val, pos.z_val),
            camera_orientation=(ori.x_val, ori.y_val, ori.z_val, ori.w_val),
        )
