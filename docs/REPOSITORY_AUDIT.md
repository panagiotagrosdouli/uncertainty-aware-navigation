# Repository Audit

This audit reviews `uncertainty-aware-navigation` as research software for MSc/PhD applications and open scientific reuse.

## Overall assessment

The project has a strong scientific premise: uncertainty-aware path planning is a focused and defensible robotics problem that connects naturally to SLAM, VIO, risk-aware navigation, and safe autonomy. The current repository is scientifically promising but still at prototype maturity because evaluation scripts, deterministic outputs, benchmark tables, and implementation evidence must be completed before any performance claims are made.

## Scores

| Dimension | Score / 10 | Rationale |
|---|---:|---|
| Scientific quality | 7 | Clear research question and measurable hypothesis; missing completed experiments. |
| Software engineering | 5 | Package metadata and tooling exist; planner API, tests, and experiment runner need hardening. |
| Documentation | 6 | README and first experiment plan are now stronger; detailed API and reproducibility docs remain needed. |
| Reproducibility | 5 | Configuration-driven intent exists; manifests and deterministic output validation are not complete. |
| Presentation | 6 | Good portfolio positioning; needs generated diagrams, figures, and result tables. |
| MSc readiness | 7 | Strong enough as a focused thesis project after experiment runner and tests are completed. |
| PhD readiness | 5 | Needs deeper novelty, baselines, uncertainty calibration, and simulation/robot validation. |

## Scientific audit

### Strengths

- The problem is focused: risk-sensitive planning under map uncertainty.
- The hypothesis is measurable: compare uncertainty-aware planning against shortest-path baselines.
- The connection to broader robust autonomy research is clear.
- The repository avoids unsupported state-of-the-art claims.

### High-priority issues

1. **No validated benchmark results.** This matters because admissions committees and labs need to distinguish implemented evidence from planned work.
2. **Uncertainty model needs formal definition.** This matters because different uncertainty-generation assumptions can change the experimental conclusion.
3. **Baselines must be explicit.** This matters because A*, Dijkstra, and risk-weighted variants must share the same graph, map, and evaluation logic for fair comparison.

## Engineering audit

### Strengths

- Python packaging is configured through `pyproject.toml`.
- Ruff, Black, and pytest are configured.
- The repository appears suitable for a clean `src/` layout.

### High-priority issues

1. **Common planner interface required.** A shared `Planner` protocol or abstract base class should expose `plan(map, start, goal, config)`.
2. **Typed data structures required.** Occupancy maps, uncertainty maps, paths, and metric records should use dataclasses or typed containers.
3. **Experiment runner should produce machine-readable outputs.** CSV, JSON, and manifest files are required for reproducibility.

## Documentation audit

### Strengths

- README now gives scientific positioning, limitations, and reporting policy.
- `docs/first_experiment_plan.md` defines an initial experimental design.

### High-priority issues

1. **Missing API reference.** Users need documented planner, map, and evaluation modules.
2. **Missing reproducibility guide.** Exact command structure, expected outputs, and result-validation rules must be explicit.
3. **Missing architecture diagram.** A diagram helps readers understand data flow quickly.

## Architecture audit

Recommended architecture:

```text
src/uncertainty_navigation/
  core/          # GridMap, UncertaintyMap, Path, Pose/GridIndex
  planning/      # A*, Dijkstra, uncertainty-aware A*
  evaluation/    # success, collision proxy, risk, path length, runtime
  experiments/   # orchestration helpers
  visualization/ # map and path plotting
  utils/         # config loading, logging, seeds
```

This separation prevents experiment scripts from becoming the only place where algorithms exist.

## Performance audit

Current priorities are correctness and reproducibility. Once correctness tests exist, performance should be measured with:

- runtime per map size;
- node expansions;
- memory use for grid representations;
- scaling from small maps to large maps;
- effect of uncertainty penalty on search complexity.

No performance numbers should be reported before scripts generate them.

## Testing audit

Required tests:

- A* returns the known shortest path on toy maps.
- Dijkstra and A* agree when the heuristic is admissible.
- Uncertainty penalty changes route selection on a controlled map.
- Blocked maps return a documented failure result, not an exception.
- Seeded map generation is deterministic.
- Metric computation handles empty and failed paths.

## Reproducibility audit

A valid experiment run should save:

- configuration file copy;
- random seeds;
- Git commit SHA;
- Python version and platform;
- dependency versions;
- raw per-trial results;
- aggregated summary;
- plots generated from raw results.

## UX / research presentation audit

The repository should expose one command for the first experiment and one command for figure generation. The README should show expected output file names, but not numerical values until generated and committed.

## Priority roadmap

| Priority | Improvement | Motivation |
|---:|---|---|
| P0 | Implement deterministic first experiment runner | Required before any research claim. |
| P0 | Add tests for planner correctness | Prevents invalid comparisons. |
| P0 | Add result manifest generation | Makes runs reproducible and auditable. |
| P1 | Add architecture and pipeline diagrams | Improves research presentation. |
| P1 | Add benchmark table template | Encourages honest reporting without fake values. |
| P2 | Add ROS2/Nav2 notes only after core benchmark is stable | Avoids over-scoping. |

## Completed in this hardening pass

- Rewrote README as a research landing page.
- Added this repository audit.
- Added contribution, conduct, security, changelog, Docker, pre-commit, and GitHub template scaffolding.
- Strengthened CI quality gates.

## Remaining future work

The next scientific milestone is to implement and validate the first experiment end-to-end, then generate plots and tables from deterministic outputs.