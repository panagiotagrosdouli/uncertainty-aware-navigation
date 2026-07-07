"""Robot state model for online navigation simulations."""
from __future__ import annotations

from dataclasses import dataclass, field

Cell = tuple[int, int]


@dataclass
class RobotState:
    """State tracked during an online navigation rollout."""

    position: Cell
    goal: Cell
    path_history: list[Cell] = field(default_factory=list)
    steps: int = 0
    replans: int = 0

    def __post_init__(self) -> None:
        """Initialize path history with the initial position."""

        if not self.path_history:
            self.path_history.append(self.position)

    @property
    def at_goal(self) -> bool:
        """Return whether the robot has reached the goal."""

        return self.position == self.goal

    def move_to(self, next_position: Cell) -> None:
        """Move the robot to a neighboring cell and update history."""

        self.position = next_position
        self.steps += 1
        self.path_history.append(next_position)

    def register_replan(self) -> None:
        """Record that a replanning event occurred."""

        self.replans += 1
