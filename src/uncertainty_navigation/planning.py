"""Deterministic grid planners for uncertainty-aware navigation experiments."""

from __future__ import annotations

import heapq
import math
import time
from collections.abc import Iterable

from uncertainty_navigation.core import Cell, GridMap, PlanResult


class GridPlanner:
    """A* planner with optional uncertainty and occupancy penalties."""

    def __init__(
        self,
        *,
        name: str = "astar",
        lambda_uncertainty: float = 0.0,
        lambda_occupancy: float = 0.0,
        use_heuristic: bool = True,
    ) -> None:
        if lambda_uncertainty < 0.0 or lambda_occupancy < 0.0:
            raise ValueError("planning penalties must be non-negative")
        self.name = name
        self.lambda_uncertainty = lambda_uncertainty
        self.lambda_occupancy = lambda_occupancy
        self.use_heuristic = use_heuristic

    def plan(self, grid: GridMap, start: Cell, goal: Cell) -> PlanResult:
        """Plan a path from ``start`` to ``goal``.

        Args:
            grid: Occupancy and uncertainty map.
            start: Start cell as ``(row, col)``.
            goal: Goal cell as ``(row, col)``.

        Returns:
            A :class:`PlanResult` with path and diagnostics. Failed planning returns
            ``success=False`` rather than raising, unless inputs are malformed.
        """

        start_time = time.perf_counter()
        if grid.is_blocked(start):
            return PlanResult(self.name, (), False, math.inf, 0, 0.0, "start_blocked")
        if grid.is_blocked(goal):
            return PlanResult(self.name, (), False, math.inf, 0, 0.0, "goal_blocked")

        frontier: list[tuple[float, Cell]] = [(0.0, start)]
        came_from: dict[Cell, Cell | None] = {start: None}
        cost_so_far: dict[Cell, float] = {start: 0.0}
        expanded = 0

        while frontier:
            _, current = heapq.heappop(frontier)
            expanded += 1
            if current == goal:
                runtime = time.perf_counter() - start_time
                path = tuple(_reconstruct_path(came_from, goal))
                return PlanResult(
                    planner=self.name,
                    path=path,
                    success=True,
                    cost=cost_so_far[goal],
                    expanded_nodes=expanded,
                    runtime_s=runtime,
                )

            for neighbor in _neighbors(current):
                if grid.is_blocked(neighbor):
                    continue
                step_cost = self._cell_cost(grid, neighbor)
                new_cost = cost_so_far[current] + step_cost
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost
                    if self.use_heuristic:
                        priority += _manhattan(neighbor, goal)
                    heapq.heappush(frontier, (priority, neighbor))
                    came_from[neighbor] = current

        runtime = time.perf_counter() - start_time
        return PlanResult(self.name, (), False, math.inf, expanded, runtime, "no_path")

    def _cell_cost(self, grid: GridMap, cell: Cell) -> float:
        return (
            1.0
            + self.lambda_uncertainty * float(grid.uncertainty[cell])
            + self.lambda_occupancy * float(grid.occupancy[cell])
        )


def _neighbors(cell: Cell) -> Iterable[Cell]:
    row, col = cell
    yield row - 1, col
    yield row + 1, col
    yield row, col - 1
    yield row, col + 1


def _manhattan(a: Cell, b: Cell) -> float:
    return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))


def _reconstruct_path(came_from: dict[Cell, Cell | None], goal: Cell) -> list[Cell]:
    current: Cell | None = goal
    path: list[Cell] = []
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path
