from __future__ import annotations

import argparse
import json
from pathlib import Path

from uanav.belief_space import run_belief_space_demo
from uanav.demo import run_all as run_demo_all
from uanav.demo import run_synthetic_demo
from uanav.research_platform import run_research_smoke
from uanav.robot_showcase import generate_showcase, make_gif, make_mp4, validate_artifacts

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SHOWCASE_CONFIG = REPOSITORY_ROOT / "configs" / "showcase" / "robot_research_demo.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run uncertainty-aware navigation workflows.")
    parser.add_argument(
        "--mode",
        choices=(
            "smoke",
            "demo",
            "baseline",
            "dynamic",
            "belief-space",
            "calibration",
            "ablation",
            "robot-demo",
            "media",
            "ros2",
            "full",
        ),
        default="demo",
        help="Workflow to execute.",
    )
    return parser.parse_args()


def run_robot_demo() -> dict:
    return generate_showcase(
        SHOWCASE_CONFIG,
        7,
        "results/demo/robot_showcase",
    )


def run_media() -> dict:
    root = Path("results/demo/robot_showcase")
    if not (root / "robot_states.csv").exists():
        run_robot_demo()
    gif = make_gif(
        root,
        "assets/gifs/uncertainty_navigation_robot_demo.gif",
        stride=8,
        fps=4,
    )
    mp4: Path | None = None
    codec_error: str | None = None
    try:
        mp4 = make_mp4(
            root,
            "assets/videos/uncertainty_navigation_robot_demo.mp4",
            stride=4,
            fps=8,
        )
        mirror = Path("results/videos/uncertainty_navigation_robot_demo.mp4")
        mirror.parent.mkdir(parents=True, exist_ok=True)
        mirror.write_bytes(mp4.read_bytes())
    except (OSError, RuntimeError, ValueError) as exc:
        codec_error = str(exc)
    validation = validate_artifacts(root, gif, mp4)
    return {
        "gif": str(gif),
        "mp4": str(mp4) if mp4 else None,
        "codec_error": codec_error,
        "validation": validation,
    }


def run_mode(mode: str) -> dict:
    if mode == "smoke":
        synthetic = run_synthetic_demo()
        belief_space = run_belief_space_demo()
        research = run_research_smoke()
        return {
            "mode": mode,
            "synthetic_success": synthetic["metrics"]["mission_completion"],
            "belief_space_success": belief_space.success,
            "research_selected_candidate": research["selected_candidate"],
        }
    if mode == "belief-space":
        return run_belief_space_demo().to_dict()
    if mode in {"dynamic", "calibration", "ablation"}:
        return {"mode": mode, "research": run_research_smoke()}
    if mode == "baseline":
        return {"mode": mode, "demo": run_demo_all()}
    if mode == "robot-demo":
        return {"mode": mode, "robot_demo": run_robot_demo()}
    if mode == "media":
        return {"mode": mode, "media": run_media()}
    if mode == "ros2":
        return {
            "mode": mode,
            "status": "ROS2 Validation Pending",
            "blocker": "ROS2 runtime and message packages are not available in the current execution environment.",
        }
    if mode == "full":
        return {
            "mode": mode,
            "demo": run_demo_all(),
            "belief_space": run_belief_space_demo().to_dict(),
            "research": run_research_smoke(),
            "robot_demo": run_robot_demo(),
            "media": run_media(),
        }
    return {"mode": mode, "demo": run_demo_all()}


if __name__ == "__main__":
    print(json.dumps(run_mode(parse_args().mode), indent=2, default=str))
