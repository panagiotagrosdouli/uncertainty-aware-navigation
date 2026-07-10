# Recoverability and Safety Rejection

Status: **Research Prototype** · **Synthetic Demo** · **Pending Real-World Validation**

The recoverability layer is evaluated independently from nominal planner cost. A candidate route is rejected when it loses graph connectivity to configured safe fallback regions or when its analytical recoverability score falls below the configured threshold.

## Implemented signals

- reachable safe set from one or more fallback regions,
- fallback-path existence and worst fallback-path cost,
- minimum escape-route count,
- route redundancy proxy,
- dead-end depth,
- minimum future clearance,
- safe-stop reachability,
- first path index at which recoverability is lost.

## Hard-constraint semantics

A route with attractive distance, information-gain, or risk-weighted utility remains inadmissible when the separate safety layer reports any violation. Rejection records include the candidate identifier, measured value, threshold, timestep, violated constraint, and a human-readable explanation.

The implementation is an analytical grid-world research prototype. It is not a formal viability-kernel computation, an exact POMDP solution, or evidence of real-robot safety.
