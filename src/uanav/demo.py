from __future__ import annotations

import heapq
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

import imageio.v2 as imageio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import distance_transform_edt

Point = tuple[int, int]


@dataclass(frozen=True)
class ScenarioConfig:
    seed: int = 7
    height: int = 30
    width: int = 42
    start: Point = (2, 2)
    goal: Point = (26, 38)
    planner: str = "risk_aware_astar"
    lambda_uncertainty: float = 4.0
    lambda_risk: float = 8.0
    lambda_recoverability: float = 1.5
    risk_threshold: float = 0.62
    uncertainty_threshold: float = 0.72
    recoverability_threshold: float = 0.22
    max_steps: int = 220
    output_dir: str = "results"


def ensure_dirs(root: str | Path = "results") -> Path:
    root = Path(root)
    for sub in ["", "metrics", "figures", "videos", "reports"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    for sub in ["assets/figures", "assets/gifs", "assets/videos"]:
        Path(sub).mkdir(parents=True, exist_ok=True)
    return root


def save_json(path: str | Path, data: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_world(cfg: ScenarioConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(cfg.seed)
    occ = np.zeros((cfg.height, cfg.width), dtype=int)
    occ[0, :] = occ[-1, :] = occ[:, 0] = occ[:, -1] = 1
    occ[7:24, 14] = 1
    occ[7:24, 27] = 1
    occ[15, 14:28] = 1
    occ[11, 14] = 0
    occ[21, 27] = 0
    occ[15, 20] = 0
    occ[5:10, 32:36] = 1
    occ[20:26, 7:11] = 1
    for _ in range(65):
        row = int(rng.integers(2, cfg.height - 2))
        col = int(rng.integers(2, cfg.width - 2))
        if (row, col) not in [cfg.start, cfg.goal] and rng.random() < 0.28:
            occ[row, col] = 1
    occ[cfg.start] = occ[cfg.goal] = 0
    belief = np.full_like(occ, 0.5, dtype=float)
    belief[occ == 1] = 0.92
    belief[occ == 0] = 0.18
    unknown = np.zeros_like(belief)
    unknown[4:18, 18:31] = 1
    unknown[17:27, 2:18] = 1
    belief[unknown == 1] = 0.5
    belief = np.clip(belief + rng.normal(0, 0.07, belief.shape), 0.02, 0.98)
    uncertainty = normalized_uncertainty(belief, unknown)
    risk = risk_map(occ, unknown, uncertainty)
    recoverability = recoverability_map(occ, risk)
    return occ, belief, unknown, uncertainty, risk, recoverability


def normalized_uncertainty(belief: np.ndarray, unknown: np.ndarray) -> np.ndarray:
    probability = np.clip(belief, 1e-6, 1 - 1e-6)
    entropy = -(probability * np.log2(probability) + (1 - probability) * np.log2(1 - probability))
    frontier = unknown.astype(float)
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        frontier += 0.25 * np.roll(np.roll(unknown, dx, axis=0), dy, axis=1)
    return np.clip(0.65 * entropy + 0.35 * np.clip(frontier / 2, 0, 1), 0, 1)


def risk_map(occupancy: np.ndarray, unknown: np.ndarray, uncertainty: np.ndarray) -> np.ndarray:
    dist = distance_transform_edt(1 - occupancy.astype(int))
    proximity = np.exp(-dist / 2.2)
    narrow = np.clip((3.0 - dist) / 3.0, 0, 1)
    risk = 0.45 * proximity + 0.25 * unknown + 0.20 * uncertainty + 0.10 * narrow
    risk[occupancy.astype(bool)] = 1.0
    return np.clip(risk, 0, 1)


def recoverability_map(occupancy: np.ndarray, risk: np.ndarray) -> np.ndarray:
    clearance = np.clip(distance_transform_edt(1 - occupancy.astype(int)) / 6.0, 0, 1)
    score = 0.65 * clearance + 0.35 * (1 - risk)
    score[occupancy.astype(bool)] = 0.0
    return np.clip(score, 0, 1)


def astar(
    occupancy: np.ndarray,
    start: Point,
    goal: Point,
    uncertainty: np.ndarray | None = None,
    risk: np.ndarray | None = None,
    recoverability: np.ndarray | None = None,
    lambda_uncertainty: float = 0.0,
    lambda_risk: float = 0.0,
    lambda_recoverability: float = 0.0,
    heuristic: bool = True,
) -> tuple[list[Point], dict]:
    t0 = time.perf_counter()
    uncertainty = np.zeros_like(occupancy, dtype=float) if uncertainty is None else uncertainty
    risk = np.zeros_like(occupancy, dtype=float) if risk is None else risk
    recoverability = np.zeros_like(occupancy, dtype=float) if recoverability is None else recoverability
    queue: list[tuple[float, Point]] = [(0.0, start)]
    came: dict[Point, Point | None] = {start: None}
    cost: dict[Point, float] = {start: 0.0}
    expanded = 0
    while queue:
        _, current = heapq.heappop(queue)
        expanded += 1
        if current == goal:
            break
        for nb in neighbors(current, occupancy.shape):
            if occupancy[nb] >= 1:
                continue
            step = max(
                0.05,
                1
                + lambda_uncertainty * uncertainty[nb]
                + lambda_risk * risk[nb]
                - lambda_recoverability * recoverability[nb],
            )
            new_cost = cost[current] + float(step)
            if new_cost < cost.get(nb, math.inf):
                cost[nb] = new_cost
                came[nb] = current
                h = abs(nb[0] - goal[0]) + abs(nb[1] - goal[1]) if heuristic else 0
                heapq.heappush(queue, (new_cost + h, nb))
    path: list[Point] = []
    if goal in came:
        cur: Point | None = goal
        while cur is not None:
            path.append(cur)
            cur = came[cur]
        path.reverse()
    return path, {
        "planning_time_s": time.perf_counter() - t0,
        "expanded_nodes": expanded,
        "cost": cost.get(goal, math.inf),
    }


def neighbors(point: Point, shape: tuple[int, int]):
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nb = (point[0] + dx, point[1] + dy)
        if 0 <= nb[0] < shape[0] and 0 <= nb[1] < shape[1]:
            yield nb


def validate_path(path: list[Point], occupancy: np.ndarray) -> bool:
    return (
        bool(path)
        and all(occupancy[p] == 0 for p in path)
        and all(
            abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
            for a, b in zip(path, path[1:], strict=False)
        )
    )


def plan(
    cfg: ScenarioConfig,
    occ: np.ndarray,
    start: Point,
    goal: Point,
    uncertainty: np.ndarray,
    risk: np.ndarray,
    recoverability: np.ndarray,
    planner: str | None = None,
):
    planner = planner or cfg.planner
    if planner == "dijkstra":
        return astar(occ, start, goal, heuristic=False)
    if planner == "astar":
        return astar(occ, start, goal)
    if planner == "uncertainty_aware_astar":
        return astar(occ, start, goal, uncertainty=uncertainty, lambda_uncertainty=cfg.lambda_uncertainty)
    if planner == "recoverability_aware_astar":
        return astar(
            occ,
            start,
            goal,
            uncertainty,
            risk,
            recoverability,
            cfg.lambda_uncertainty,
            cfg.lambda_risk,
            cfg.lambda_recoverability,
        )
    return astar(occ, start, goal, uncertainty, risk, recoverability, cfg.lambda_uncertainty, cfg.lambda_risk, 0.0)


def safety_state(
    pos: Point,
    risk: np.ndarray,
    uncertainty: np.ndarray,
    recoverability: np.ndarray,
    cfg: ScenarioConfig,
    blocked: bool = False,
) -> str:
    rv, uv, qv = float(risk[pos]), float(uncertainty[pos]), float(recoverability[pos])
    if blocked:
        return "REROUTE"
    if rv > cfg.risk_threshold and qv < cfg.recoverability_threshold:
        return "STOP"
    if rv > cfg.risk_threshold:
        return "REROUTE"
    if uv > cfg.uncertainty_threshold:
        return "CAUTION"
    if qv < cfg.recoverability_threshold:
        return "SLOW_DOWN"
    return "NORMAL"


def run_synthetic_demo(cfg: ScenarioConfig | None = None) -> dict:
    cfg = ScenarioConfig() if cfg is None else cfg
    out = ensure_dirs(cfg.output_dir)
    occ, belief, unknown, uncertainty, risk, recoverability = build_world(cfg)
    pos = cfg.start
    trajectory = [pos]
    planned_paths: list[list[Point]] = []
    events: list[dict] = []
    times: list[float] = []
    collisions = 0
    path, info = plan(cfg, occ, pos, cfg.goal, uncertainty, risk, recoverability)
    planned_paths.append(path)
    times.append(info["planning_time_s"])
    idx = 1
    for step in range(cfg.max_steps):
        blocked = not path or idx >= len(path)
        state = safety_state(pos, risk, uncertainty, recoverability, cfg, blocked)
        events.append(
            {
                "step": step,
                "row": pos[0],
                "col": pos[1],
                "risk": float(risk[pos]),
                "uncertainty": float(uncertainty[pos]),
                "recoverability": float(recoverability[pos]),
                "state": state,
                "label": "Synthetic Demo",
            }
        )
        if pos == cfg.goal:
            break
        if state in {"REROUTE", "STOP"} or blocked or step in {35, 70}:
            path, info = plan(cfg, occ, pos, cfg.goal, uncertainty, risk, recoverability)
            planned_paths.append(path)
            times.append(info["planning_time_s"])
            idx = 1
            if not path:
                break
        nxt = path[idx] if idx < len(path) else pos
        if occ[nxt] == 1:
            collisions += 1
            idx = len(path)
            continue
        pos = nxt
        trajectory.append(pos)
        idx += 1
    success = bool(pos == cfg.goal)
    metrics = compute_metrics(
        trajectory, planned_paths, risk, uncertainty, recoverability, times, success, collisions, events
    )
    np.save(out / "metrics" / "occupancy_grid.npy", occ)
    np.save(out / "metrics" / "belief_map.npy", belief)
    np.save(out / "metrics" / "uncertainty_map.npy", uncertainty)
    np.save(out / "metrics" / "risk_map.npy", risk)
    np.save(out / "metrics" / "recoverability_map.npy", recoverability)
    pd.DataFrame(
        [{"step": i, "row": p[0], "col": p[1], "label": "Synthetic Demo"} for i, p in enumerate(trajectory)]
    ).to_csv(out / "metrics" / "executed_trajectory.csv", index=False)
    pd.DataFrame(events).to_csv(out / "metrics" / "safety_events.csv", index=False)
    pd.DataFrame([metrics]).to_csv(out / "metrics" / "metrics.csv", index=False)
    save_json(out / "metrics" / "summary.json", metrics)
    save_json(
        out / "metrics" / "planned_paths.json",
        {"label": "Synthetic Demo", "paths": [[list(p) for p in path] for path in planned_paths]},
    )
    save_json(
        out / "metrics" / "mission_summary.json",
        {
            "label": "Synthetic Demo",
            "success": success,
            "limitations": "Synthetic grid-world only; not hardware validation.",
        },
    )
    return {
        "config": cfg,
        "occupancy": occ,
        "belief": belief,
        "unknown": unknown,
        "uncertainty": uncertainty,
        "risk": risk,
        "recoverability": recoverability,
        "trajectory": trajectory,
        "planned_paths": planned_paths,
        "safety_events": events,
        "metrics": metrics,
        "output_dir": str(out),
    }


def compute_metrics(
    trajectory: list[Point],
    planned_paths: list[list[Point]],
    risk: np.ndarray,
    uncertainty: np.ndarray,
    recoverability: np.ndarray,
    times: list[float],
    success: bool,
    collisions: int,
    events: list[dict],
) -> dict:
    return {
        "label": "Synthetic Demo",
        "synthetic_demo": True,
        "path_length": len(planned_paths[-1]) if planned_paths else 0,
        "executed_trajectory_length": len(trajectory),
        "travel_time_steps": max(0, len(trajectory) - 1),
        "planning_time_total_s": float(sum(times)),
        "planning_time_mean_s": float(np.mean(times)) if times else 0.0,
        "success_rate": 1.0 if success else 0.0,
        "collision_count": int(collisions),
        "near_miss_count": int(sum(1 for p in trajectory if risk[p] > 0.55)),
        "risk_exposure": float(sum(risk[p] for p in trajectory)),
        "uncertainty_exposure": float(sum(uncertainty[p] for p in trajectory)),
        "recoverability_exposure": float(np.mean([recoverability[p] for p in trajectory])),
        "mission_completion": bool(success),
        "safety_intervention_count": int(sum(1 for e in events if e["state"] != "NORMAL")),
        "replanning_count": max(0, len(planned_paths) - 1),
        "average_replanning_latency_s": float(np.mean(times[1:])) if len(times) > 1 else 0.0,
    }


def _plot_path(ax, path: list[Point], **kwargs) -> None:
    if path:
        ax.plot([p[1] for p in path], [p[0] for p in path], **kwargs)


def generate_figures(result: dict | None = None) -> list[str]:
    result = run_synthetic_demo() if result is None else result
    out = ensure_dirs(result["output_dir"])
    figdir = out / "figures"
    paths: list[str] = []
    map_specs = [
        ("occupancy_grid", result["occupancy"], "gray_r"),
        ("belief_map", result["belief"], "magma"),
        ("uncertainty_heatmap", result["uncertainty"], "viridis"),
        ("risk_heatmap", result["risk"], "inferno"),
        ("recoverability_heatmap", result["recoverability"], "cividis"),
    ]
    for name, field, cmap in map_specs:
        fig, ax = plt.subplots(figsize=(7, 5))
        im = ax.imshow(field, cmap=cmap)
        ax.set_title(name.replace("_", " ").title() + " — Synthetic Demo")
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        path = figdir / f"{name}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(str(path))

    baseline, _ = astar(result["occupancy"], result["config"].start, result["config"].goal)
    comparison_specs = [
        ("planned_vs_executed", result["occupancy"]),
        ("uncertainty_aware_vs_shortest", result["risk"]),
        ("architecture_diagram", None),
        ("navigation_pipeline_diagram", None),
    ]
    for name, bg in comparison_specs:
        fig, ax = plt.subplots(figsize=(8, 5 if bg is not None else 2))
        if bg is None:
            ax.axis("off")
            text = (
                "Config → Grid World → Uncertainty/Risk/Recoverability → Planner → Safety Supervisor → Metrics"
                if "architecture" in name
                else "Belief Update → Plan → Execute → Assess Risk → Replan"
            )
            ax.text(0.5, 0.5, text, ha="center", va="center")
        else:
            ax.imshow(bg, cmap="gray_r" if name == "planned_vs_executed" else "inferno")
            _plot_path(ax, baseline, linewidth=2, label="shortest A*")
            _plot_path(ax, result["planned_paths"][-1], linewidth=2, linestyle="--", label="risk-aware A*")
            _plot_path(ax, result["trajectory"], linewidth=2, linestyle=":", label="executed")
            ax.legend()
            ax.set_xticks([])
            ax.set_yticks([])
        ax.set_title(name.replace("_", " ").title() + " — Synthetic Demo")
        path = figdir / f"{name}.png"
        fig.tight_layout()
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(str(path))

    steps = [e["step"] for e in result["safety_events"]]
    timeline_specs = [
        ("risk_exposure_timeline", [e["risk"] for e in result["safety_events"]]),
        ("uncertainty_exposure_timeline", [e["uncertainty"] for e in result["safety_events"]]),
    ]
    for name, values in timeline_specs:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.plot(steps, values)
        ax.set_ylim(0, 1)
        ax.set_title(name.replace("_", " ").title() + " — Synthetic Demo")
        path = figdir / f"{name}.png"
        fig.tight_layout()
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(str(path))

    states = ["NORMAL", "CAUTION", "SLOW_DOWN", "REROUTE", "STOP", "MISSION_ABORT"]
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.step(steps, [states.index(e["state"]) for e in result["safety_events"]], where="post")
    ax.set_yticks(range(len(states)), states)
    ax.set_title("Safety Supervisor Timeline — Synthetic Demo")
    path = figdir / "safety_supervisor_timeline.png"
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path))
    return paths


def make_demo_media(result: dict | None = None) -> tuple[str, str]:
    result = run_synthetic_demo() if result is None else result
    out = ensure_dirs(result["output_dir"])
    frame_dir = out / "videos" / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, pos in enumerate(result["trajectory"]):
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.imshow(result["risk"], cmap="inferno", alpha=0.55)
        ax.imshow(result["occupancy"], cmap="gray_r", alpha=0.35)
        _plot_path(ax, result["planned_paths"][-1], linewidth=2, label="planned")
        _plot_path(ax, result["trajectory"][: i + 1], linewidth=2, linestyle="--", label="executed")
        ax.scatter([result["config"].start[1]], [result["config"].start[0]], marker="o", s=70)
        ax.scatter([result["config"].goal[1]], [result["config"].goal[0]], marker="*", s=120)
        ax.scatter([pos[1]], [pos[0]], marker="o", s=100)
        event = result["safety_events"][min(i, len(result["safety_events"]) - 1)]
        ax.set_title(
            "Uncertainty-Aware Navigation — Synthetic Demo\n"
            f"step={i} risk={event['risk']:.2f} uncertainty={event['uncertainty']:.2f} "
            f"recoverability={event['recoverability']:.2f} state={event['state']}"
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.legend(loc="upper right")
        fig.tight_layout()
        frame = frame_dir / f"frame_{i:04d}.png"
        fig.savefig(frame, dpi=120)
        plt.close(fig)
        frames.append(imageio.imread(frame))
    gif = str(out / "videos" / "uncertainty_aware_navigation_demo.gif")
    mp4 = str(out / "videos" / "uncertainty_aware_navigation_demo.mp4")
    imageio.mimsave(gif, frames, duration=0.12)
    imageio.mimsave(mp4, frames, fps=8)
    imageio.mimsave("assets/gifs/demo.gif", frames, duration=0.12)
    imageio.mimsave("assets/videos/demo.mp4", frames, fps=8)
    return gif, mp4


def run_benchmarks() -> pd.DataFrame:
    cfg = ScenarioConfig()
    out = ensure_dirs(cfg.output_dir)
    occ, _belief, _unknown, uncertainty, risk, recoverability = build_world(cfg)
    rows = []
    planners = ["dijkstra", "astar", "uncertainty_aware_astar", "risk_aware_astar", "recoverability_aware_astar"]
    for planner in planners:
        path, info = plan(cfg, occ, cfg.start, cfg.goal, uncertainty, risk, recoverability, planner)
        rows.append(
            {
                "label": "Synthetic Demo",
                "planner": planner,
                "success": bool(path and path[-1] == cfg.goal),
                "path_length": len(path),
                "planning_time_s": info["planning_time_s"],
                "risk_exposure": float(sum(risk[p] for p in path)) if path else math.inf,
                "uncertainty_exposure": float(sum(uncertainty[p] for p in path)) if path else math.inf,
                "recoverability_mean": float(np.mean([recoverability[p] for p in path])) if path else 0.0,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(out / "metrics" / "benchmark_summary.csv", index=False)
    report = (
        "# Benchmark Report — Synthetic Demo\n\n"
        "Generated from deterministic synthetic grid-world code. "
        "These are not real-robot or state-of-the-art results.\n\n"
        + df.to_markdown(index=False)
    )
    (out / "reports" / "benchmark_report.md").write_text(report, encoding="utf-8")
    return df


def run_all() -> dict:
    result = run_synthetic_demo()
    figures = generate_figures(result)
    gif, mp4 = make_demo_media(result)
    benchmarks = run_benchmarks()
    return {
        "label": "Synthetic Demo",
        "figures": len(figures),
        "gif": gif,
        "mp4": mp4,
        "benchmark_rows": len(benchmarks),
        "metrics": result["metrics"],
    }
