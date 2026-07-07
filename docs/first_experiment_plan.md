# First Experiment Plan

## Title

Classical shortest-path planning versus uncertainty-weighted risk-aware planning in partially observed grid maps.

## Objective

The objective of the first experiment is to test whether map uncertainty can be used as an explicit planning cost to reduce unsafe navigation behaviour in previously unknown environments.

## Research Hypothesis

A planner that penalizes uncertain regions will produce safer trajectories than a purely distance-based shortest-path planner, especially when the robot operates with incomplete or noisy map information.

## Experimental Setting

The initial environment is a two-dimensional grid map. Each cell stores two values:

1. **Occupancy probability**, representing whether the cell is likely to be free or occupied.
2. **Uncertainty value**, representing the planner's confidence about the cell state.

The robot is modeled as a point agent in the first baseline version. Later versions may include robot radius, obstacle inflation, and dynamic replanning.

## Compared Methods

### Baseline Planner

The baseline planner uses a classical shortest-path objective:

```text
cost(cell) = geometric_cost(cell)
```

Possible implementations include A* or Dijkstra search.

### Risk-Aware Planner

The uncertainty-aware planner augments the geometric cost with an uncertainty penalty:

```text
cost(cell) = geometric_cost(cell) + lambda_uncertainty * uncertainty(cell)
```

where `lambda_uncertainty` controls the strength of risk sensitivity.

## Independent Variables

- map size
- obstacle density
- uncertainty level
- sensor noise level
- start-goal distance
- uncertainty penalty weight

## Dependent Variables

- success rate
- collision rate
- path length
- traversal time
- minimum obstacle distance
- accumulated risk cost
- replanning frequency
- computation time

## Protocol

1. Generate a controlled set of grid-map environments.
2. Sample start and goal positions in valid free-space regions.
3. Generate partial or noisy observations of the map.
4. Compute a path using the baseline planner.
5. Compute a path using the uncertainty-aware planner.
6. Simulate execution or evaluate path safety on the ground-truth map.
7. Repeat over multiple random seeds.
8. Report mean ± standard deviation for all metrics.

## Initial Configuration

The first reproducible configuration is stored in:

```text
configs/first_experiment.yaml
```

## Expected Outcome

The uncertainty-aware planner is expected to reduce collision rate and accumulated risk cost, but may increase path length or traversal time. This trade-off is scientifically important because it makes the safety-efficiency relationship explicit.

## Reporting Requirements

Every result table should report:

- planner name
- number of trials
- random seeds
- mean ± standard deviation
- map-generation parameters
- uncertainty-weight parameter
- hardware or runtime environment, when computation time is reported
