# Experimental Research Questions

Status: **Research Prototype / Pending Validation**

The experiments in this repository test whether uncertainty-aware navigation improves safety and decision quality relative to deterministic shortest-path planning. All conclusions must be based on identical scenario realizations and random seeds across methods.

## RQ1 — Uncertainty exposure

Does uncertainty-aware planning reduce cumulative and maximum map-uncertainty exposure relative to standard A* and Dijkstra?

Primary outcomes: cumulative uncertainty exposure, maximum uncertainty exposure, mission success, path inefficiency ratio.

## RQ2 — Collision and near-miss risk

Does risk-aware planning reduce collision and near-miss frequency under static and dynamic hazards?

Primary outcomes: collision rate, near-miss rate, cumulative risk exposure, maximum risk exposure.

## RQ3 — Recoverability

Does recoverability-aware planning avoid dead ends and preserve feasible fallback routes to known-safe space?

Primary outcomes: dead-end entries, fallback availability, fallback path length, safe-state reachability, irrecoverable-state entries.

## RQ4 — Safety supervision

Does the safety supervisor prevent unsafe actions early enough without excessive false interventions?

Primary outcomes: intervention precision, intervention recall, false-intervention rate, missed-unsafe-condition rate, intervention lead time, successful recovery after intervention.

## RQ5 — Safety–efficiency trade-off

What path-length, completion-time, planning-latency, and computational-overhead costs accompany reductions in uncertainty and risk exposure?

Primary outcomes: path length, path inefficiency ratio, mission completion time, planning latency, replanning latency, computational overhead.

## RQ6 — Sensitivity

How sensitive are outcomes to map uncertainty, obstacle density, localization noise, dynamic-obstacle speed, prediction horizon, and planner weights?

Primary outcomes: metric trends, variance, unstable parameter regions, and Pareto-style safety–efficiency fronts.

## RQ7 — Robustness

Do observed improvements remain consistent across scenario families and multiple random seeds?

Primary outcomes: mean, standard deviation, median, interquartile range, confidence intervals where justified, failure counts, and effect sizes for paired comparisons.

## Experimental controls

- Every planner receives the same occupancy realization, belief state, dynamic-agent trajectories, localization-noise sequence, start, goal, and seed.
- The oracle-map method is an upper-bound reference, not a deployable baseline.
- Heuristic uncertainty scores are not described as probabilities unless calibration has been demonstrated.
- Failed runs remain in the audit trail and are not silently removed.
- Synthetic results are not generalized to real robots without independent validation.
