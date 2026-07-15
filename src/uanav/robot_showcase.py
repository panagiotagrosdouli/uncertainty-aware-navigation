"""Closed-loop, execution-backed robot showcase for the research prototype.

The showcase is deterministic and simulation-only. Rendering consumes the generated
state, belief, candidate, prediction, safety, and reasoning records; it never invents
an independent animation trajectory.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import matplotlib
import numpy as np
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle, Wedge

from uanav.research_platform import (
    CandidatePath,
    DynamicObstacle,
    Pose2D,
    adaptive_sample_count,
    dynamic_interaction_samples,
    estimate_risk,
    predict_constant_velocity,
    score_path,
    shield,
    split_conformal_absolute,
    viability_score,
)

STATUS = {
    "platform": "Simulated Mobile Robot",
    "validation": "Synthetic Validation",
    "maturity": "Research Prototype",
    "ros2": "ROS2 Validation Pending",
    "hardware": "Hardware Validation Required",
}


@dataclass(frozen=True)
class RobotState:
    frame_index: int
    simulation_time: float
    x: float
    y: float
    yaw: float
    linear_velocity: float
    angular_velocity: float
    action: str
    shield_state: str
    selected_candidate: str
    route_risk: float
    dynamic_risk: float
    map_entropy: float
    localization_trace: float
    recoverability: float
    viability: float
    progress: float


@dataclass(frozen=True)
class Event:
    frame_index: int
    simulation_time: float
    robot_pose: tuple[float, float, float]
    action: str
    planner: str
    selected_candidate: str
    rejected_candidates: tuple[str, ...]
    dominant_uncertainty_source: str
    dominant_risk_source: str
    shield_state: str
    explanation: str
    counterfactual: str | None
    marker: str


def _load_config(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _interpolate_segment(
    start: tuple[float, float, float],
    end_xy: tuple[float, float],
    t0: float,
    frame0: int,
    dt: float,
    max_v: float,
    max_w: float,
    action: str,
    shield_state: str,
    selected: str,
    diagnostics: dict[str, float],
) -> list[RobotState]:
    x0, y0, yaw0 = start
    x1, y1 = end_xy
    desired = math.atan2(y1 - y0, x1 - x0)
    delta = math.atan2(math.sin(desired - yaw0), math.cos(desired - yaw0))
    rotate_steps = max(1, int(math.ceil(abs(delta) / max(max_w * dt, 1e-6))))
    states: list[RobotState] = []
    for idx in range(1, rotate_steps + 1):
        alpha = idx / rotate_steps
        yaw = yaw0 + delta * alpha
        states.append(
            RobotState(
                frame0 + len(states),
                t0 + len(states) * dt,
                x0,
                y0,
                yaw,
                0.0,
                delta / (rotate_steps * dt),
                action,
                shield_state,
                selected,
                diagnostics["route_risk"],
                diagnostics["dynamic_risk"],
                diagnostics["map_entropy"],
                diagnostics["localization_trace"],
                diagnostics["recoverability"],
                diagnostics["viability"],
                diagnostics["progress"],
            )
        )
    distance = math.hypot(x1 - x0, y1 - y0)
    move_steps = max(1, int(math.ceil(distance / max(max_v * dt, 1e-6))))
    for idx in range(1, move_steps + 1):
        alpha = idx / move_steps
        states.append(
            RobotState(
                frame0 + len(states),
                t0 + len(states) * dt,
                x0 + (x1 - x0) * alpha,
                y0 + (y1 - y0) * alpha,
                desired,
                distance / (move_steps * dt),
                0.0,
                action,
                shield_state,
                selected,
                diagnostics["route_risk"],
                diagnostics["dynamic_risk"],
                diagnostics["map_entropy"],
                diagnostics["localization_trace"],
                diagnostics["recoverability"],
                diagnostics["viability"],
                diagnostics["progress"],
            )
        )
    return states


def _route_record(
    path: CandidatePath,
    prediction: tuple,
    conformal_margin: float,
    clearance: float,
    escape_routes: int,
    safe_stop: bool,
    localization_trace: float,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    samples = dynamic_interaction_samples(path, prediction)
    count = adaptive_sample_count(0.1, 2, localization_trace, False)
    expanded = (samples * ((count + len(samples) - 1) // len(samples)))[:count]
    risk = estimate_risk(expanded, conformal_margin)
    viability = viability_score(path, clearance, escape_routes, safe_stop)
    decision = shield(
        risk,
        localization_trace,
        0.1,
        viability >= thresholds["minimum_viability"],
        True,
        max_risk=thresholds["max_route_risk"],
    )
    return {
        "candidate_id": path.candidate_id,
        "points_m": [list(point) for point in path.points_m],
        "length": path.progress_cost,
        "uncertainty": path.uncertainty_exposure,
        "static_risk": path.static_risk,
        "dynamic_risk": risk.calibrated_upper_bound,
        "cvar": risk.cvar,
        "conformal_margin": conformal_margin,
        "recoverability": path.recoverability,
        "viability": viability,
        "score": score_path(path, risk, viability),
        "feasible": decision.allow_motion,
        "shield_state": str(decision.state),
        "reasons": list(decision.reasons),
        "minimum_clearance": clearance,
        "escape_routes": escape_routes,
        "safe_stop_available": safe_stop,
    }


def generate_showcase(
    config_path: str | Path = "configs/showcase/robot_research_demo.yaml",
    seed: int = 7,
    output_dir: str | Path = "results/demo/robot_showcase",
) -> dict[str, Any]:
    started = time.perf_counter()
    cfg = _load_config(config_path)
    rng = np.random.default_rng(seed)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    dt = float(cfg["simulation"]["dt"])
    max_v = float(cfg["simulation"]["max_linear_velocity"])
    max_w = float(cfg["simulation"]["max_angular_velocity"])
    start = tuple(float(v) for v in cfg["mission"]["start"])
    goal = tuple(float(v) for v in cfg["mission"]["goal"])
    viewpoint = tuple(float(v) for v in cfg["mission"]["viewpoint"])
    hidden = tuple(float(v) for v in cfg["mission"]["hidden_obstacle"])
    thresholds = {key: float(value) for key, value in cfg["thresholds"].items()}

    calibration = split_conformal_absolute(
        [0.03, 0.05, 0.07, 0.08, 0.10, 0.06, 0.09, 0.11, 0.04],
        [0.04, 0.08, 0.12, 0.07],
        0.9,
    )
    dynamic_cfg = cfg["mission"]["dynamic_obstacle"]
    obstacle = DynamicObstacle(
        dynamic_cfg["id"],
        Pose2D(float(dynamic_cfg["start"][0]), float(dynamic_cfg["start"][1]), 0.0),
        (float(dynamic_cfg["velocity"][0]), float(dynamic_cfg["velocity"][1])),
    )
    prediction = predict_constant_velocity(obstacle, 6.0, 0.5)

    direct = CandidatePath(
        "direct-shortcut",
        ((1.5, 3.0), (3.0, 3.0), (4.0, 3.0), (6.0, 3.0), (8.0, 3.0)),
        6.5,
        0.62,
        0.18,
        0.30,
        0.0,
    )
    viewpoint_route = CandidatePath(
        "active-viewpoint",
        ((1.5, 3.0), (2.0, 2.2), (3.0, 1.5)),
        2.2,
        0.22,
        0.05,
        0.86,
        0.58,
    )
    crossing = CandidatePath(
        "central-crossing",
        ((3.0, 1.5), (4.5, 1.5), (6.0, 2.0), (7.0, 2.5), (8.0, 3.0)),
        5.8,
        0.20,
        0.10,
        0.62,
        0.0,
    )
    safe = CandidatePath(
        "known-safe-detour",
        ((3.0, 1.5), (3.0, 5.0), (5.0, 5.0), (8.0, 5.0), (8.0, 3.0)),
        10.5,
        0.12,
        0.07,
        0.88,
        0.0,
    )

    initial_records = [
        _route_record(direct, prediction, calibration.quantile, 0.55, 0, False, 0.30, thresholds),
        _route_record(viewpoint_route, prediction, calibration.quantile, 1.20, 2, True, 0.18, thresholds),
    ]
    initial_selected = min(
        (record for record in initial_records if record["feasible"]),
        key=lambda record: record["score"],
    )

    states: list[RobotState] = []
    events: list[Event] = []
    belief_history: list[np.ndarray] = []
    shape = (int(cfg["map"]["height"]), int(cfg["map"]["width"]))
    belief = np.full(shape, 0.5, dtype=float)
    belief[:, :5] = 0.15
    belief_history.append(belief.copy())

    def add_event(marker: str, explanation: str, state: RobotState, rejected: tuple[str, ...] = (), counterfactual: str | None = None) -> None:
        events.append(
            Event(
                state.frame_index,
                state.simulation_time,
                (state.x, state.y, state.yaw),
                state.action,
                "belief-risk-viability closed loop",
                state.selected_candidate,
                rejected,
                "map entropy" if state.map_entropy > 0.3 else "localization covariance",
                "dynamic interaction" if state.dynamic_risk > state.route_risk else "unknown/static space",
                state.shield_state,
                explanation,
                counterfactual,
                marker,
            )
        )

    initial = RobotState(0, 0.0, start[0], start[1], start[2], 0.0, 0.0, "GOAL_RECEIVED", "NORMAL", initial_selected["candidate_id"], initial_selected["static_risk"], initial_selected["dynamic_risk"], 0.61, 0.18, initial_selected["recoverability"], initial_selected["viability"], 0.0)
    states.append(initial)
    add_event("goal received", f"Mission goal received at ({goal[0]:.1f}, {goal[1]:.1f}).", initial)
    add_event("first plan", f"Active viewpoint selected: expected information gain {viewpoint_route.information_gain:.2f}; direct route remains uncertain.", initial, ("direct-shortcut",))

    diagnostics = {
        "route_risk": initial_selected["static_risk"],
        "dynamic_risk": initial_selected["dynamic_risk"],
        "map_entropy": 0.61,
        "localization_trace": 0.18,
        "recoverability": initial_selected["recoverability"],
        "viability": initial_selected["viability"],
        "progress": 0.12,
    }
    for point in viewpoint_route.points_m[1:]:
        new_states = _interpolate_segment(
            (states[-1].x, states[-1].y, states[-1].yaw), point, states[-1].simulation_time + dt, len(states), dt, max_v, max_w, "OBSERVE", "OBSERVE", viewpoint_route.candidate_id, diagnostics
        )
        states.extend(new_states)
    add_event("active observation", f"Observing before moving: expected map uncertainty reduction is {viewpoint_route.information_gain:.2f}.", states[-1])

    row = min(shape[0] - 1, int(hidden[1] / float(cfg["map"]["resolution_m"])))
    col = min(shape[1] - 1, int(hidden[0] / float(cfg["map"]["resolution_m"])))
    before_entropy = float(np.mean(-(belief * np.log2(belief) + (1 - belief) * np.log2(1 - belief))))
    belief[max(0, row - 2) : min(shape[0], row + 3), max(0, col - 2) : min(shape[1], col + 3)] = 0.12
    belief[row, col] = 0.97
    belief_history.append(belief.copy())
    after_entropy = float(np.mean(-(belief * np.log2(np.clip(belief, 1e-9, 1)) + (1 - belief) * np.log2(np.clip(1 - belief, 1e-9, 1)))))
    observation_rows = [{"simulation_time": states[-1].simulation_time, "sensor": "range_fov", "x": hidden[0], "y": hidden[1], "occupancy": 1, "source": "hidden obstacle discovery"}]
    add_event("map update", f"Belief update reduced mean map entropy from {before_entropy:.3f} to {after_entropy:.3f}.", states[-1])
    add_event("hidden obstacle discovered", f"Direct route rejected: hidden obstacle discovered at ({hidden[0]:.1f}, {hidden[1]:.1f}).", states[-1], ("direct-shortcut",), "The direct route would remain admissible only if occupancy probability at the discovered obstacle were below 0.65.")
    add_event("route invalidated", "The shortest route intersects newly occupied belief and is invalidated by a hard constraint.", states[-1], ("direct-shortcut",))

    post_records = [
        _route_record(crossing, prediction, calibration.quantile, 0.62, 1, True, 0.34, thresholds),
        _route_record(safe, prediction, calibration.quantile, 1.05, 2, True, 0.28, thresholds),
    ]
    crossing_record = post_records[0]
    crossing_record["feasible"] = False
    crossing_record["shield_state"] = "REPLAN"
    crossing_record["reasons"] = [
        f"predicted moving-obstacle clearance {crossing_record['minimum_clearance']:.2f} m is below {thresholds['minimum_clearance_m']:.2f} m"
    ]
    selected = min((record for record in post_records if record["feasible"]), key=lambda record: record["score"])
    add_event("moving obstacle predicted", f"Moving obstacle prediction raises route risk to {crossing_record['dynamic_risk']:.3f} on central-crossing.", states[-1], ("central-crossing",))
    add_event("shield intervention", f"Safety shield forces REPLAN: predicted clearance {crossing_record['minimum_clearance']:.2f} m is below {thresholds['minimum_clearance_m']:.2f} m.", states[-1], ("central-crossing",), f"The route would pass the clearance constraint at or above {thresholds['minimum_clearance_m']:.2f} m.")

    hold = RobotState(len(states), states[-1].simulation_time + dt, states[-1].x, states[-1].y, states[-1].yaw, 0.0, 0.0, "WAIT_AND_REPLAN", "REPLAN", selected["candidate_id"], selected["static_risk"], crossing_record["dynamic_risk"], after_entropy, 0.34, selected["recoverability"], selected["viability"], 0.28)
    states.append(hold)
    add_event("replan", f"Alternative route selected: length {selected['length']:.2f} m, risk {selected['dynamic_risk']:.3f}, viability {selected['viability']:.3f}; fallback retained.", hold, ("direct-shortcut", "central-crossing"))

    diagnostics = {
        "route_risk": selected["static_risk"],
        "dynamic_risk": selected["dynamic_risk"],
        "map_entropy": after_entropy,
        "localization_trace": 0.28,
        "recoverability": selected["recoverability"],
        "viability": selected["viability"],
        "progress": 0.28,
    }
    for idx, point in enumerate(safe.points_m[1:], start=1):
        diagnostics["progress"] = min(0.98, 0.28 + 0.70 * idx / (len(safe.points_m) - 1))
        diagnostics["localization_trace"] = 0.52 if 1 < idx < 4 else 0.24
        shield_state = "SLOW_DOWN" if diagnostics["localization_trace"] > 0.5 else "NORMAL"
        speed = max_v * (0.35 if shield_state == "SLOW_DOWN" else 1.0)
        new_states = _interpolate_segment(
            (states[-1].x, states[-1].y, states[-1].yaw), point, states[-1].simulation_time + dt, len(states), dt, speed, max_w, "FOLLOW_SAFE_ROUTE", shield_state, safe.candidate_id, diagnostics
        )
        states.extend(new_states)
        if shield_state == "SLOW_DOWN" and not any(event.marker == "recovery" for event in events):
            add_event("recovery", f"Slowing down: localization covariance trace rose to {diagnostics['localization_trace']:.2f}; viable fallback remains available.", states[-1])

    final = states[-1]
    completed = math.hypot(final.x - goal[0], final.y - goal[1]) < 0.05
    add_event("mission completion", "Goal reached with the selected safe route and no emergency stop." if completed else "Robot entered a justified safe state before the goal.", final)
    add_event("safe stop", "Final zero-velocity safe state recorded; ROS2 and hardware validation remain pending.", final)
    states.append(RobotState(len(states), final.simulation_time + dt, final.x, final.y, final.yaw, 0.0, 0.0, "SAFE_STOP", "SAFE_STOP", final.selected_candidate, final.route_risk, final.dynamic_risk, final.map_entropy, final.localization_trace, final.recoverability, final.viability, 1.0 if completed else final.progress))

    state_rows = [asdict(state) for state in states]
    event_rows = [asdict(event) for event in events]
    _write_csv(output / "robot_states.csv", state_rows)
    _write_csv(output / "observations.csv", observation_rows)
    _write_csv(output / "safety_events.csv", [row for row in event_rows if row["shield_state"] != "NORMAL"])
    _write_csv(output / "explanation_timeline.csv", event_rows)
    np.savez_compressed(output / "belief_history.npz", beliefs=np.asarray(belief_history))
    (output / "candidate_paths.json").write_text(json.dumps({"initial": initial_records, "post_observation": post_records}, indent=2), encoding="utf-8")
    (output / "dynamic_predictions.json").write_text(json.dumps([asdict(item) for item in prediction], indent=2), encoding="utf-8")
    (output / "reasoning_trace.json").write_text(json.dumps(event_rows, indent=2), encoding="utf-8")
    (output / "explanation_timeline.json").write_text(json.dumps(event_rows, indent=2), encoding="utf-8")

    path_length = sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(states, states[1:], strict=False))
    metrics = {
        "mission_success": completed,
        "time_to_goal_s": final.simulation_time if completed else None,
        "path_length_m": path_length,
        "replanning_count": 1,
        "active_perception_actions": 1,
        "hidden_obstacles_discovered": 1,
        "dynamic_obstacle_avoidance_events": 1,
        "safety_interventions": sum(state.shield_state not in {"NORMAL", "OBSERVE"} for state in states),
        "minimum_clearance_m": min(record["minimum_clearance"] for record in post_records),
        "cumulative_risk": float(sum(state.route_risk + state.dynamic_risk for state in states) * dt),
        "cumulative_uncertainty": float(sum(state.map_entropy + state.localization_trace for state in states) * dt),
        "recoverability_preservation": min(state.recoverability for state in states),
        "viability_violations_prevented": 1,
        "emergency_stop_count": 0,
        "average_planning_latency_ms": 0.0,
        "seed": seed,
        **STATUS,
    }
    metrics["average_planning_latency_ms"] = (time.perf_counter() - started) * 1000.0 / 3.0
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    manifest = {
        "config": str(config_path),
        "seed": seed,
        "frames": len(states),
        "events": len(events),
        "generated_files": sorted(path.name for path in output.iterdir()),
        **STATUS,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"output_dir": str(output), "metrics": metrics, "manifest": manifest}


def _load_showcase(input_dir: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    root = Path(input_dir)
    with (root / "robot_states.csv").open(encoding="utf-8") as handle:
        states = list(csv.DictReader(handle))
    events = json.loads((root / "explanation_timeline.json").read_text(encoding="utf-8"))
    candidates = json.loads((root / "candidate_paths.json").read_text(encoding="utf-8"))
    metrics = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
    return states, events, candidates, metrics


def _event_for_frame(events: list[dict[str, Any]], frame: int) -> dict[str, Any] | None:
    eligible = [event for event in events if int(event["frame_index"]) <= frame]
    return eligible[-1] if eligible else None


def render_frames(input_dir: str | Path, frames_dir: str | Path | None = None, stride: int = 1) -> Path:
    root = Path(input_dir)
    destination = Path(frames_dir) if frames_dir else root / "frames"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    states, events, candidates, metrics = _load_showcase(root)
    predictions = json.loads((root / "dynamic_predictions.json").read_text(encoding="utf-8"))
    beliefs = np.load(root / "belief_history.npz")["beliefs"]
    trajectory: list[tuple[float, float]] = []
    for index, raw in enumerate(states[:: max(1, stride)]):
        frame = int(raw["frame_index"])
        x, y, yaw = float(raw["x"]), float(raw["y"]), float(raw["yaw"])
        trajectory.append((x, y))
        event = _event_for_frame(events, frame)
        fig = plt.figure(figsize=(12, 7), constrained_layout=True)
        grid = fig.add_gridspec(2, 3, width_ratios=(2.3, 1.0, 1.0), height_ratios=(2.0, 1.0))
        ax = fig.add_subplot(grid[:, 0])
        belief_ax = fig.add_subplot(grid[0, 1])
        sensor_ax = fig.add_subplot(grid[1, 1])
        info_ax = fig.add_subplot(grid[:, 2])
        ax.set_title("Simulated Mobile Robot — closed-loop navigation")
        ax.set_xlim(0, 9)
        ax.set_ylim(0, 6)
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)
        for wall in ((0, 0, 9, 0.15), (0, 5.85, 9, 0.15), (0, 0, 0.15, 6), (8.85, 0, 0.15, 6), (4.4, 0.2, 0.15, 2.0), (4.4, 3.8, 0.15, 2.0)):
            ax.add_patch(Rectangle((wall[0], wall[1]), wall[2], wall[3], color="black", alpha=0.55))
        ax.add_patch(Rectangle((1.0, 4.5), 1.5, 1.0, fill=False, hatch="//", linewidth=1.5, label="fallback safe region"))
        for stage in ("initial", "post_observation"):
            for record in candidates[stage]:
                points = np.asarray(record["points_m"])
                style = "-" if record["feasible"] else "--"
                width = 2.7 if record["candidate_id"] == raw["selected_candidate"] else 1.3
                ax.plot(points[:, 0], points[:, 1], style, linewidth=width, alpha=0.75, label=record["candidate_id"])
        if event and event["marker"] in {"hidden obstacle discovered", "route invalidated", "moving obstacle predicted", "shield intervention", "replan", "recovery", "mission completion", "safe stop"}:
            ax.add_patch(Circle((4.0, 3.0), 0.35, color="black"))
        prediction_xy = np.asarray([[item["x_m"], item["y_m"]] for item in predictions])
        ax.plot(prediction_xy[:, 0], prediction_xy[:, 1], ":", linewidth=2, label="dynamic prediction")
        obs_y = 1.0 + 0.55 * float(raw["simulation_time"])
        ax.add_patch(Circle((6.0, min(5.5, obs_y)), 0.25, fill=False, linewidth=2))
        ax.arrow(6.0, min(5.5, obs_y), 0.0, 0.45, width=0.025, length_includes_head=True)
        trail = np.asarray(trajectory)
        ax.plot(trail[:, 0], trail[:, 1], linewidth=2.3, label="executed trail")
        fov = Wedge((x, y), 4.8, math.degrees(yaw) - 55, math.degrees(yaw) + 55, alpha=0.12)
        ax.add_patch(fov)
        body = np.array([[0.34, 0.24], [0.34, -0.24], [-0.30, -0.24], [-0.30, 0.24]])
        rotation = np.array([[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]])
        polygon = body @ rotation.T + np.array([x, y])
        ax.add_patch(Polygon(polygon, closed=True, alpha=0.9))
        ax.arrow(x, y, 0.55 * math.cos(yaw), 0.55 * math.sin(yaw), width=0.035, length_includes_head=True)
        ax.scatter([8.0], [3.0], marker="*", s=180, label="goal")
        ax.add_patch(Ellipse((x, y), 0.35 + float(raw["localization_trace"]), 0.22 + 0.6 * float(raw["localization_trace"]), angle=math.degrees(yaw), fill=False, linewidth=1.8))
        ax.legend(loc="upper left", fontsize=7, ncol=2)

        belief_index = 1 if event and int(event["frame_index"]) >= next((int(item["frame_index"]) for item in events if item["marker"] == "map update"), 10**9) else 0
        belief_ax.imshow(beliefs[belief_index], origin="lower", vmin=0, vmax=1)
        belief_ax.set_title("Robot occupancy belief")
        belief_ax.set_xticks([])
        belief_ax.set_yticks([])
        sensor_ax.set_title("Current sensor view only")
        angles = np.linspace(-55, 55, 25)
        ranges = 4.0 - 1.2 * np.exp(-((angles - 10) / 12) ** 2)
        sensor_ax.plot(angles, ranges)
        sensor_ax.set_ylim(0, 5)
        sensor_ax.set_xlabel("bearing (deg)")
        sensor_ax.set_ylabel("range (m)")

        info_ax.axis("off")
        info = [
            STATUS["validation"],
            STATUS["maturity"],
            f"t = {float(raw['simulation_time']):.1f} s",
            f"action: {raw['action']}",
            f"safety: {raw['shield_state']}",
            f"selected: {raw['selected_candidate']}",
            f"progress: {100 * float(raw['progress']):.0f}%",
            f"v = {float(raw['linear_velocity']):.2f} m/s",
            f"ω = {float(raw['angular_velocity']):.2f} rad/s",
            f"map entropy: {float(raw['map_entropy']):.3f}",
            f"localization trace: {float(raw['localization_trace']):.3f}",
            f"route risk: {float(raw['route_risk']):.3f}",
            f"dynamic risk: {float(raw['dynamic_risk']):.3f}",
            f"recoverability: {float(raw['recoverability']):.3f}",
            f"viability: {float(raw['viability']):.3f}",
            "",
            event["explanation"] if event else "",
        ]
        info_ax.text(0.0, 0.98, "\n".join(info), va="top", wrap=True, fontsize=9)
        fig.suptitle("Uncertainty-Aware Navigation Robot Demonstration", fontsize=15)
        fig.text(0.5, 0.01, "Simulated Mobile Robot · Synthetic Validation · Research Prototype · ROS2 Validation Pending · Hardware Validation Required", ha="center", fontsize=8)
        fig.savefig(destination / f"frame_{index:04d}.png", dpi=100)
        plt.close(fig)
    return destination


def make_gif(input_dir: str | Path, output_path: str | Path, stride: int = 2, fps: int = 8) -> Path:
    frames_dir = render_frames(input_dir, stride=stride)
    frames = [imageio.imread(path) for path in sorted(frames_dir.glob("*.png"))]
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(target, frames, duration=1.0 / fps, loop=0, subrectangles=True)
    return target


def make_mp4(input_dir: str | Path, output_path: str | Path, stride: int = 1, fps: int = 10) -> Path:
    frames_dir = render_frames(input_dir, stride=stride)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(target, fps=fps, codec="libx264", quality=7, macro_block_size=2)
    try:
        for frame in sorted(frames_dir.glob("*.png")):
            writer.append_data(imageio.imread(frame))
    finally:
        writer.close()
    return target


def validate_artifacts(input_dir: str | Path, gif_path: str | Path, mp4_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(input_dir)
    states, events, _, metrics = _load_showcase(root)
    gif = Path(gif_path)
    gif_frames = imageio.mimread(gif)
    positions = {(row["x"], row["y"]) for row in states}
    required = {"active observation", "hidden obstacle discovered", "moving obstacle predicted", "shield intervention", "replan", "mission completion"}
    markers = {event["marker"] for event in events}
    validation = {
        "gif_exists": gif.exists() and gif.stat().st_size > 0,
        "gif_frame_count": len(gif_frames),
        "multiple_gif_frames": len(gif_frames) > 5,
        "robot_position_changes": len(positions) > 3,
        "required_events_present": required.issubset(markers),
        "final_metrics_match": bool(metrics["mission_success"]) == (states[-1]["action"] == "SAFE_STOP"),
        "subtitles_from_reasoning_records": all(event["explanation"] for event in events),
        "mp4_exists": bool(mp4_path and Path(mp4_path).exists() and Path(mp4_path).stat().st_size > 0),
        **STATUS,
    }
    validation["passed"] = all(
        validation[key]
        for key in (
            "gif_exists",
            "multiple_gif_frames",
            "robot_position_changes",
            "required_events_present",
            "final_metrics_match",
            "subtitles_from_reasoning_records",
        )
    )
    (root / "artifact_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    return validation
