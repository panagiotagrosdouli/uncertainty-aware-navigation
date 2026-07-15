from __future__ import annotations

import argparse

from uanav.robot_showcase import make_gif, validate_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the robot showcase GIF from generated logs.")
    parser.add_argument("--input", default="results/demo/robot_showcase")
    parser.add_argument("--output", default="assets/gifs/uncertainty_navigation_robot_demo.gif")
    parser.add_argument("--stride", type=int, default=2)
    parser.add_argument("--fps", type=int, default=8)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output = make_gif(args.input, args.output, args.stride, args.fps)
    print(output)
    print(validate_artifacts(args.input, output))
