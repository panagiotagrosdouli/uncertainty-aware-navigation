# Uncertainty-Aware Navigation

**Risk-aware mobile robot navigation under map uncertainty**

This repository contains research code for studying uncertainty-aware navigation in previously unknown environments. The central question is how a mobile robot can use uncertainty estimates about the environment to make safer navigation decisions under partial observability.

The project focuses on the connection between environment representation, uncertainty estimation, risk-sensitive planning, and navigation safety. It is intended as a focused research repository that can support a diploma thesis, technical report, or future paper submission.

## Research Question

How can a mobile robot use map uncertainty to reduce unsafe navigation behaviour in previously unknown environments?

## Core Idea

Classical navigation planners often optimize geometric cost, path length, or traversal time. In unknown environments, however, the robot must also reason about uncertainty: unknown space, noisy observations, incomplete maps, and dynamic changes.

This project investigates a planning formulation in which navigation cost is influenced not only by distance, but also by estimated environmental uncertainty and risk.

## Scope

This repository focuses on one research problem:

**uncertainty-aware risk-sensitive navigation for mobile robots.**

It does not attempt to address language-based planning, multi-robot coordination, foundation models, semantic mapping, or general autonomous driving. These topics are intentionally outside the scope of this repository.

## Method Overview

The planned research pipeline consists of:

1. Environment representation using occupancy and uncertainty maps.
2. Uncertainty estimation from partial observations.
3. Risk-aware path planning using uncertainty-weighted cost functions.
4. Safety-oriented replanning under uncertain map conditions.
5. Evaluation against classical navigation baselines.

## Planned Evaluation

The method will be evaluated against baseline planners such as A*, Dijkstra, or standard ROS navigation pipelines using controlled simulation scenarios.

Evaluation metrics will include:

- success rate
- collision rate
- path length
- traversal time
- minimum obstacle distance
- accumulated risk cost
- replanning frequency
- computation time

All reported results should include the number of trials, random seeds, and mean ± standard deviation.

## Repository Structure

```text
.
├── configs/          # Experiment and planner configurations
├── docs/             # Technical notes and methodology
├── experiments/      # Reproducible experiment scripts
├── figures/          # Diagrams and result figures
├── paper/            # Notes toward a technical report or paper
├── src/              # Source code
└── README.md
```

## Current Status

This repository is at the initial research-setup stage. The first development target is a reproducible baseline comparing classical shortest-path planning with uncertainty-weighted risk-aware planning in controlled grid-map environments.

## First Experiment

The first experiment compares a classical shortest-path planner with an uncertainty-weighted planner on controlled grid maps.

The initial hypothesis is that adding an uncertainty penalty to the planning cost can reduce unsafe navigation behaviour, especially in partially observed maps, at the cost of longer or more conservative paths.

See [`docs/first_experiment_plan.md`](docs/first_experiment_plan.md) for the initial experimental design.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Reproducibility

Experiments should be configured through files in `configs/`, executed through scripts in `experiments/`, and reported with explicit random seeds, number of trials, and summary statistics.

## Citation

If you use this repository, please cite it using the metadata in [`CITATION.cff`](CITATION.cff).

## License

This project is released under the MIT License. See [`LICENSE`](LICENSE) for details.
