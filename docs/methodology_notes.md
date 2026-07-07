# Methodology Notes

## Problem Definition

The project studies navigation under map uncertainty. The robot must plan a path from a start state to a goal state while using an imperfect representation of the environment.

## Map Representation

The first version uses grid maps with two layers:

- an occupancy layer
- an uncertainty layer

The occupancy layer describes whether a cell is likely to be traversable. The uncertainty layer describes how reliable the map estimate is.

## Risk-Aware Cost

The initial cost formulation is:

```text
J = J_geometry + lambda_uncertainty * J_uncertainty
```

This formulation allows the planner to trade off path efficiency against uncertainty avoidance.

## Safety Interpretation

A lower-risk path is not necessarily the shortest path. In this project, safety is operationalized through measurable quantities such as collision rate, minimum obstacle distance, and accumulated risk cost.

## Reproducibility Principle

All experiments should be repeatable from configuration files. Reported results should include random seeds, number of trials, planner parameters, and summary statistics.
