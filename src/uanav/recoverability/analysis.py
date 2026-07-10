"""Hard recoverability checks for candidate paths in partially observed maps."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

Point = tuple[int, int]


@dataclass(frozen=True)
class RecoverabilityAssessment:
    candidate_id: str
    admissible: bool
    fallback_path_exists: bool
    fallback_path_cost: float
    escape_route_count: int
    route_redundancy: float
    dead_end_depth: int
    minimum_future_clearance: float
    safe_stop_reachable: bool
    first_irrecoverable_index: int | None
    rejection_reason: str | None


def _neighbors(point: Point, shape: tuple[int, int]) -> list[Point]:
    row, col = point
    result: list[Point] = []
    for drow, dcol in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nxt = (row + drow, col + dcol)
        if 0 <= nxt[0] < shape[0] and 0 <= nxt[1] < shape[1]:
            result.append(nxt)
    return result


def traversable_mask(
    occupancy_probability: np.ndarray,
    uncertainty: np.ndarray,
    occupancy_threshold: float = 0.65,
    uncertainty_threshold: float = 0.80,
) -> np.ndarray:
    """Return cells that are sufficiently likely to be free and sufficiently known."""
    if occupancy_probability.shape != uncertainty.shape:
        raise ValueError("occupancy_probability and uncertainty must have equal shape")
    return (occupancy_probability < occupancy_threshold) & (uncertainty <= uncertainty_threshold)


def reachable_safe_set(
    occupancy_probability: np.ndarray,
    uncertainty: np.ndarray,
    safe_regions: set[Point],
    occupancy_threshold: float = 0.65,
    uncertainty_threshold: float = 0.80,
) -> np.ndarray:
    """Compute all cells connected to at least one valid safe fallback region."""
    traversable = traversable_mask(
        occupancy_probability,
        uncertainty,
        occupancy_threshold=occupancy_threshold,
        uncertainty_threshold=uncertainty_threshold,
    )
    reachable = np.zeros_like(traversable, dtype=bool)
    queue: deque[Point] = deque()
    for point in safe_regions:
        if traversable[point]:
            reachable[point] = True
            queue.append(point)
    while queue:
        current = queue.popleft()
        for nxt in _neighbors(current, traversable.shape):
            if traversable[nxt] and not reachable[nxt]:
                reachable[nxt] = True
                queue.append(nxt)
    return reachable


def _distance_to_safe_region(start: Point, traversable: np.ndarray, safe_regions: set[Point]) -> float:
    if start in safe_regions:
        return 0.0
    queue: deque[tuple[Point, int]] = deque([(start, 0)])
    visited = {start}
    while queue:
        current, distance = queue.popleft()
        for nxt in _neighbors(current, traversable.shape):
            if nxt in visited or not traversable[nxt]:
                continue
            if nxt in safe_regions:
                return float(distance + 1)
            visited.add(nxt)
            queue.append((nxt, distance + 1))
    return float("inf")


def _clearance(point: Point, traversable: np.ndarray) -> float:
    blocked = np.argwhere(~traversable)
    if blocked.size == 0:
        return float(max(traversable.shape))
    delta = blocked - np.asarray(point)
    return float(np.sqrt(np.sum(delta * delta, axis=1)).min())


def assess_path_recoverability(
    candidate_id: str,
    path: list[Point],
    occupancy_probability: np.ndarray,
    uncertainty: np.ndarray,
    safe_regions: set[Point],
    recoverability_threshold: float = 0.50,
    occupancy_threshold: float = 0.65,
    uncertainty_threshold: float = 0.80,
) -> RecoverabilityAssessment:
    """Assess a candidate and reject it at the first state without a safe fallback."""
    if not path:
        return RecoverabilityAssessment(
            candidate_id=candidate_id,
            admissible=False,
            fallback_path_exists=False,
            fallback_path_cost=float("inf"),
            escape_route_count=0,
            route_redundancy=0.0,
            dead_end_depth=0,
            minimum_future_clearance=0.0,
            safe_stop_reachable=False,
            first_irrecoverable_index=0,
            rejection_reason="Candidate path is empty.",
        )

    traversable = traversable_mask(
        occupancy_probability,
        uncertainty,
        occupancy_threshold=occupancy_threshold,
        uncertainty_threshold=uncertainty_threshold,
    )
    safe_set = reachable_safe_set(
        occupancy_probability,
        uncertainty,
        safe_regions,
        occupancy_threshold=occupancy_threshold,
        uncertainty_threshold=uncertainty_threshold,
    )

    first_irrecoverable: int | None = None
    clearances: list[float] = []
    escape_counts: list[int] = []
    fallback_costs: list[float] = []
    dead_end_depth = 0
    current_dead_end = 0

    for index, point in enumerate(path):
        if not traversable[point] or not safe_set[point]:
            first_irrecoverable = index
            break
        neighbors = [nxt for nxt in _neighbors(point, traversable.shape) if traversable[nxt]]
        escape_counts.append(len(neighbors))
        if len(neighbors) <= 1:
            current_dead_end += 1
            dead_end_depth = max(dead_end_depth, current_dead_end)
        else:
            current_dead_end = 0
        clearances.append(_clearance(point, traversable))
        fallback_costs.append(_distance_to_safe_region(point, traversable, safe_regions))

    fallback_exists = first_irrecoverable is None
    minimum_clearance = min(clearances, default=0.0)
    minimum_escape_routes = min(escape_counts, default=0)
    route_redundancy = min(1.0, minimum_escape_routes / 3.0)
    fallback_cost = max(fallback_costs, default=float("inf"))
    score = 0.45 * route_redundancy + 0.35 * min(1.0, minimum_clearance / 3.0)
    score += 0.20 if fallback_exists else 0.0
    admissible = fallback_exists and score >= recoverability_threshold

    if first_irrecoverable is not None:
        reason = f"Fallback path is lost at candidate index {first_irrecoverable}."
    elif not admissible:
        reason = (
            f"Recoverability score {score:.3f} is below the required threshold "
            f"{recoverability_threshold:.3f}."
        )
    else:
        reason = None

    return RecoverabilityAssessment(
        candidate_id=candidate_id,
        admissible=admissible,
        fallback_path_exists=fallback_exists,
        fallback_path_cost=fallback_cost,
        escape_route_count=minimum_escape_routes,
        route_redundancy=route_redundancy,
        dead_end_depth=dead_end_depth,
        minimum_future_clearance=minimum_clearance,
        safe_stop_reachable=fallback_exists,
        first_irrecoverable_index=first_irrecoverable,
        rejection_reason=reason,
    )
