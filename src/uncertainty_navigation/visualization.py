"""Visualization utilities for occupancy, uncertainty, and planned paths."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

Cell = tuple[int, int]


def plot_map_with_path(
    occupancy: np.ndarray,
    path: list[Cell] | None,
    output_path: str | Path,
    title: str = "Planned path",
) -> None:
    """Save a visualization of an occupancy map and optional path."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure()
    plt.imshow(occupancy, origin="upper")
    if path:
        rows = [cell[0] for cell in path]
        cols = [cell[1] for cell in path]
        plt.plot(cols, rows, linewidth=2)
        plt.scatter([cols[0], cols[-1]], [rows[0], rows[-1]], marker="o")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def plot_uncertainty_map(
    uncertainty: np.ndarray,
    output_path: str | Path,
    title: str = "Uncertainty map",
) -> None:
    """Save a heatmap of the uncertainty layer."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure()
    plt.imshow(uncertainty, origin="upper")
    plt.colorbar(label="uncertainty")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
