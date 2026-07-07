"""Classical A* path planner for grid maps."""

from __future__ import annotations

import heapq
from collections.abc import Callable

import numpy as np

Cell = tuple[int, int]
CostFunction = Callable[[Cell], float]


def zero_cost(_cell: Cell) -> float:
    """Return zero additional traversal cost."""

    return 0.0


def manhattan_distance(a: Cell, b: Cell) -> float:
    """Compute Manhattan distance between two grid cells."""

    return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))


def neighbors(cell: Cell, shape: tuple[int, int]) -> list[Cell]:
    """Return four-connected neighbors inside the grid."""

    row, col = cell
    candidates = [
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    ]
    height, width = shape
    return [(r, c) for r, c in candidates if 0 <= r < height and 0 <= c < width]


def reconstruct_path(came_from: dict[Cell, Cell], current: Cell) -> list[Cell]:
    """Reconstruct a path from A* predecessor links."""

    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def astar(
    occupancy: np.ndarray,
    start: Cell,
    goal: Cell,
    cost_fn: CostFunction | None = None,
) -> list[Cell] | None:
    """Run A* search on a binary occupancy grid.

    Parameters
    ----------
    occupancy:
        Grid where 1 denotes obstacle and 0 denotes free space.
    start:
        Start cell.
    goal:
        Goal cell.
    cost_fn:
        Optional additional traversal cost for each visited cell.

    Returns
    -------
    list[Cell] | None
        Path from start to goal, or ``None`` if no path exists.
    """

    if occupancy[start] == 1 or occupancy[goal] == 1:
        return None

    if cost_fn is None:
        cost_fn = zero_cost

    open_set: list[tuple[float, Cell]] = []
    heapq.heappush(open_set, (0.0, start))

    came_from: dict[Cell, Cell] = {}
    g_score: dict[Cell, float] = {start: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in neighbors(current, occupancy.shape):
            if occupancy[neighbor] == 1:
                continue

            tentative_g = g_score[current] + 1.0 + float(cost_fn(neighbor))
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + manhattan_distance(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))

    return None
