from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import cv2
import msgpackrpc
import numpy as np

from simulator.eventcam.event_generator import EventGenerator
from simulator.io.airsim_frame_source import AirSimFrameSource


@dataclass
class PhaseBConfig:
    profile: str
    ip: str
    vehicle: str
    duration_s: int
    save_events: bool
    save_frames: bool
    output_root: str = "runs/phase_b"
    camera_name: str = "0"
    event_width: int = 320
    event_height: int = 240
    tolerance: float = 0.2
    max_events_per_pixel: int = 5
    max_total_events_per_frame: int = 250_000
    sample_hz: float = 20.0


DEFAULT_PROFILES: dict[str, dict[str, float | int | str]] = {
    "baseline_night": {
        "event_width": 320,
        "event_height": 240,
        "tolerance": 0.2,
        "max_events_per_pixel": 5,
        "max_total_events_per_frame": 200_000,
        "sample_hz": 20.0,
        "camera_name": "0",
    }
}


def resolve_profile(name: str) -> dict[str, float | int | str]:
    if name not in DEFAULT_PROFILES:
        available = ", ".join(sorted(DEFAULT_PROFILES))
        raise ValueError(f"Unknown profile '{name}'. Available profiles: {available}")
    return DEFAULT_PROFILES[name]


def build_config(
    profile: str,
    ip: str,
    vehicle: str,
    duration_s: int,
    save_events: bool,
    save_frames: bool,
    output_root: str,
) -> PhaseBConfig:
    profile_cfg = resolve_profile(profile)
    return PhaseBConfig(
        profile=profile,
        ip=ip,
        vehicle=vehicle,
        duration_s=duration_s,
        save_events=save_events,
        save_frames=save_frames,
        output_root=output_root,
        camera_name=str(profile_cfg["camera_name"]),
        event_width=int(profile_cfg["event_width"]),
        event_height=int(profile_cfg["event_height"]),
        tolerance=float(profile_cfg["tolerance"]),
        max_events_per_pixel=int(profile_cfg["max_events_per_pixel"]),
        max_total_events_per_frame=int(profile_cfg["max_total_events_per_frame"]),
        sample_hz=float(profile_cfg["sample_hz"]),
    )


def _make_run_dirs(root: str) -> tuple[Path, Path, Path]:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(root) / stamp
    frames_dir = run_dir / "frames"
    events_dir = run_dir / "events"
    frames_dir.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, frames_dir, events_dir


def run_phase_b(cfg: PhaseBConfig) -> int:
    run_dir, frames_dir, events_dir = _make_run_dirs(cfg.output_root)

    source = AirSimFrameSource(ip=cfg.ip, vehicle_name=cfg.vehicle, camera_name=cfg.camera_name)
    try:
        source.connect()
    except msgpackrpc.error.TransportError as exc:
        raise SystemExit(
            "Could not connect to AirSim RPC server at "
            f"{cfg.ip}:41451 for Phase B run. "
            f"Ensure AirSim is running and vehicle '{cfg.vehicle}' is available. "
            f"Details: {exc}"
        )

    evgen = EventGenerator(
        width=cfg.event_width,
        height=cfg.event_height,
        tol=cfg.tolerance,
        max_events_per_pixel=cfg.max_events_per_pixel,
        max_total_events_per_frame=cfg.max_total_events_per_frame,
    )

    metadata_path = run_dir / "frame_metadata.csv"
    events_path = run_dir / "events.csv"
    summary_path = run_dir / "summary.json"

    total_frames = 0
    total_events = 0
    start_wall = time.time()
    end_wall = start_wall + cfg.duration_s
    period = 1.0 / cfg.sample_hz

    with metadata_path.open("w", newline="", encoding="utf-8") as meta_f, events_path.open(
        "w", newline="", encoding="utf-8"
    ) as ev_f:
        meta_writer = csv.writer(meta_f)
        meta_writer.writerow(
            [
                "frame_idx",
                "timestamp_us",
                "cam_x",
                "cam_y",
                "cam_z",
                "qx",
                "qy",
                "qz",
                "qw",
                "num_events",
            ]
        )

        ev_writer = csv.writer(ev_f)
        ev_writer.writerow(["x", "y", "timestamp_us", "pol"])

        while time.time() < end_wall:
            tick_start = time.time()

            frame = source.capture()
            batch = evgen.image_callback(frame.image_rgb, frame.timestamp_us)

            num_events = int(batch.events.shape[0])
            total_events += num_events
            total_frames += 1

            if cfg.save_events and num_events > 0:
                ev_writer.writerows(batch.events.tolist())

            if cfg.save_frames:
                frame_bgr = cv2.cvtColor(frame.image_rgb, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(frames_dir / f"scene_{total_frames:06d}.png"), frame_bgr)

                event_vis = np.zeros((cfg.event_height, cfg.event_width, 3), dtype=np.uint8)
                event_vis[batch.event_image > 0] = (0, 0, 255)
                event_vis[batch.event_image < 0] = (255, 0, 0)
                cv2.imwrite(str(events_dir / f"event_{total_frames:06d}.png"), event_vis)

            px, py, pz = frame.camera_position
            qx, qy, qz, qw = frame.camera_orientation
            meta_writer.writerow(
                [
                    total_frames,
                    frame.timestamp_us,
                    px,
                    py,
                    pz,
                    qx,
                    qy,
                    qz,
                    qw,
                    num_events,
                ]
            )

            elapsed = time.time() - tick_start
            if elapsed < period:
                time.sleep(period - elapsed)

    duration_actual = time.time() - start_wall
    summary = {
        "profile": cfg.profile,
        "run_dir": str(run_dir),
        "frames": total_frames,
        "events": total_events,
        "duration_s": round(duration_actual, 3),
        "avg_events_per_frame": float(total_events / total_frames) if total_frames > 0 else 0.0,
        "config": asdict(cfg),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Phase B run completed: {run_dir}")
    print(f"Frames: {total_frames}")
    print(f"Events: {total_events}")
    print(f"Duration(s): {duration_actual:.2f}")
    return 0
