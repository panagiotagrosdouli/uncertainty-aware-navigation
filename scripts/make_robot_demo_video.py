from __future__ import annotations

import argparse
import json
from pathlib import Path

from uanav.robot_showcase import make_mp4, validate_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the robot showcase MP4 from generated logs.")
    parser.add_argument("--input", default="results/demo/robot_showcase")
    parser.add_argument("--output", default="assets/videos/uncertainty_navigation_robot_demo.mp4")
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--fps", type=int, default=10)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    target = make_mp4(args.input, args.output, args.stride, args.fps)
    mirror = Path("results/videos/uncertainty_navigation_robot_demo.mp4")
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_bytes(Path(target).read_bytes())
    gif = Path("assets/gifs/uncertainty_navigation_robot_demo.gif")
    print(json.dumps(validate_artifacts(args.input, gif, target), indent=2))
