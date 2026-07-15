from __future__ import annotations

import csv
import json
import math

import imageio.v2 as imageio

from scripts.run_all import run_mode
from uanav.robot_showcase import generate_showcase, make_gif, validate_artifacts


def test_robot_showcase_is_deterministic_and_synchronized(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_showcase(output_dir=first)
    generate_showcase(output_dir=second)
    assert (first / "candidate_paths.json").read_text() == (second / "candidate_paths.json").read_text()
    with (first / "robot_states.csv").open() as handle:
        states = list(csv.DictReader(handle))
    assert len(states) > 20
    assert len({(row["x"], row["y"]) for row in states}) > 3
    assert float(states[-1]["linear_velocity"]) == 0.0
    assert states[-1]["shield_state"] == "SAFE_STOP"
    moving = [row for row in states if float(row["linear_velocity"]) > 0]
    assert all(math.isfinite(float(row["yaw"])) for row in moving)
    events = json.loads((first / "explanation_timeline.json").read_text())
    markers = {event["marker"] for event in events}
    assert {"active observation", "hidden obstacle discovered", "shield intervention", "replan"} <= markers


def test_gif_generation_has_multiple_frames(tmp_path) -> None:
    root = tmp_path / "showcase"
    generate_showcase(output_dir=root)
    gif = make_gif(root, tmp_path / "demo.gif", stride=8, fps=4)
    assert gif.exists()
    assert len(imageio.mimread(gif)) > 5
    validation = validate_artifacts(root, gif)
    assert validation["passed"]


def test_robot_demo_and_media_modes(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    robot = run_mode("robot-demo")
    assert robot["robot_demo"]["metrics"]["mission_success"]
    media = run_mode("media")
    assert media["media"]["validation"]["passed"]
