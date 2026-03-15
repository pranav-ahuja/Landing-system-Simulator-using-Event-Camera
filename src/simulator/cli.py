from __future__ import annotations

import argparse

from simulator.phase_b import build_config, run_phase_b


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulator CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a configured simulator phase/profile")
    p_run.add_argument("--profile", required=True, help="Profile name (for now: baseline_night)")
    p_run.add_argument("--duration", type=int, default=120, help="Run duration in seconds")
    p_run.add_argument("--ip", default="127.0.0.1", help="AirSim RPC IP")
    p_run.add_argument("--vehicle", default="SimpleFlight", help="AirSim vehicle name")
    p_run.add_argument("--save-events", action="store_true", help="Persist raw events CSV")
    p_run.add_argument("--save-frames", action="store_true", help="Persist scene/event images")
    p_run.add_argument(
        "--output-root",
        default="runs/phase_b",
        help="Root folder for run artifacts",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        cfg = build_config(
            profile=args.profile,
            ip=args.ip,
            vehicle=args.vehicle,
            duration_s=args.duration,
            save_events=args.save_events,
            save_frames=args.save_frames,
            output_root=args.output_root,
        )
        raise SystemExit(run_phase_b(cfg))

    raise SystemExit("Unknown command")


if __name__ == "__main__":
    main()
