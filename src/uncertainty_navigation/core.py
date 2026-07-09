"""Core typed data structures for uncertainty-aware grid navigation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

GridArray: TypeAlias = NDArray[np.float64]
BoolGrid: TypeAlias = NDArray[np.bool_]
Cell: TypeAlias = tuple[int, int]


@dataclass(frozen=True)
class GridMap:
    """Occupancy and uncertainty map used by planners and evaluators.

    Attributes:
        occupancy: Floating-point occupancy probabilities in ``[0, 1]``.
        uncertainty: Floating-point uncertainty values in ``[0, 1]``.
        obstacle_threshold: Occupancy values greater than or equal to this value are blocked.
    """

    occupancy: GridArray
    uncertainty: GridArray
    obstacle_threshold: float = 0.5

    def __post_init__(self) -> None:
        if self.occupancy.shape != self.uncertainty.shape:
            raise ValueError("occupancy and uncertainty maps must have identical shapes")
        if self.occupancy.ndim != 2:
            raise ValueError("grid maps must be two-dimensional")
        if not 0.0 <= self.obstacle_threshold <= 1.0:
            raise ValueError("obstacle_threshold must be in [0, 1]")

    @property
    def shape(self) -> tuple[int, int]:
        """Return the ``(height, width)`` shape."""

        return self.occupancy.shape

    def in_bounds(self, cell: Cell) -> bool:
        """Return whether a grid cell lies inside the map."""

        row, col = cell
        height, width = self.shape
        return 0 <= row < height and 0 <= col < width

    def is_blocked(self, cell: Cell) -> bool:
        """Return whether a grid cell is occupied or out of bounds."""

        if not self.in_bounds(cell):
            return True
        return bool(self.occupancy[cell] >= self.obstacle_threshold)

    def traversable_mask(self) -> BoolGrid:
        """Return a boolean mask where ``True`` means traversable."""

        return self.occupancy < self.obstacle_threshold


@dataclass(frozen=True)
class PlanResult:
    """Planner output with diagnostics required for reproducible evaluation."""

    planner: str
    path: tuple[Cell, ...]
    success: bool
    cost: float
    expanded_nodes: int
    runtime_s: float
    reason: str = ""

    @property
    def path_length(self) -> int:
        """Return the number of cells in the path."""

        return len(self.path)


@dataclass(frozen=True)
class TrialMetrics:
    """Per-trial metrics saved by experiment runners."""

    seed: int
    planner: str
    success: bool
    collision: bool
    path_length: int
    accumulated_uncertainty: float
    accumulated_occupancy: float
    min_obstacle_distance: float
    expanded_nodes: int
    runtime_s: float
    cost: float
