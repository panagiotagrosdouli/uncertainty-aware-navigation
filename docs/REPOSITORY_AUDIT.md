# Repository Audit

This audit reviews `uncertainty-aware-navigation` as research software for MSc/PhD applications and open scientific reuse.

## Overall assessment

The project has a strong scientific premise: uncertainty-aware path planning is a focused and defensible robotics problem that connects naturally to SLAM, VIO, risk-aware navigation, and safe autonomy. The repository now includes a minimal deterministic experiment scaffold, but it remains prototype maturity until generated outputs, plots, and broader ablations are reviewed and committed.

## Scores

| Dimension | Score / 10 | Rationale |
|---|---:|---|
| Scientific quality | 7 | Clear research question, measurable hypothesis, and first synthetic diagnostic scaffold. |
| Software engineering | 6 | Typed package modules, planner baseline, simulation generator, and tests now exist; API can still mature. |
| Documentation | 7 | README, first experiment plan, audit, and reporting policy are clear; API docs remain needed. |
| Reproducibility | 6 | Config-driven runner saves raw CSV, summary JSON, manifest, and generated report; artifacts still need CI integration. |
| Presentation | 6 | Good portfolio positioning; needs generated heatmaps, path figures, and benchmark report pages. |
| MSc readiness | 8 | Strong focused thesis foundation after first experiment and tests. |
| PhD readiness | 6 | Needs deeper novelty, ablations, uncertainty calibration, dynamic replanning, and simulation/robot validation. |

## Scientific audit

### Strengths

- The problem is focused: risk-sensitive planning under map uncertainty.
- The hypothesis is measurable: compare uncertainty-aware planning against shortest-path baselines.
- The connection to broader robust autonomy research is clear.
- The repository avoids unsupported state-of-the-art claims.
- A deterministic synthetic diagnostic experiment now exists.

### High-priority issues

1. **Ablation studies are still missing.** This matters because one uncertainty weight cannot establish robustness.
2. **Uncertainty model needs deeper formal validation.** This matters because different uncertainty-generation assumptions can change the conclusion.
3. **Baselines should expand.** This matters because A*, Dijkstra, weighted A*, and risk-aware variants should be compared under shared evaluation logic.

## Engineering audit

### Strengths

- Python packaging is configured through `pyproject.toml`.
- Ruff, Black, and pytest are configured.
- Typed core data structures, planner, simulator, evaluator, and experiment runner now exist.
- Failed planning returns structured results instead of unhandled errors.

### High-priority issues

1. **Planner interface should become protocol-based.** A shared `Planner` protocol would make new planners interchangeable.
2. **Experiment runner should add visualization.** Path overlays and uncertainty heatmaps are needed for interpretability.
3. **CI should upload generated reports as artifacts.** This would make reproducibility visible during pull requests.

## Documentation audit

### Strengths

- README gives scientific positioning, limitations, and reporting policy.
- `docs/first_experiment_plan.md` defines the initial experimental design.
- This audit records repository maturity and remaining gaps.

### High-priority issues

1. **Missing API reference.** Users need documented planner, map, and evaluation modules.
2. **Missing reproducibility guide.** Exact command structure, expected outputs, and result-validation rules should be expanded.
3. **Missing architecture diagram.** A generated diagram helps readers understand data flow quickly.

## Architecture audit

Current architecture:

```text
src/uncertainty_navigation/
  core.py          # GridMap, PlanResult, TrialMetrics
  planning.py      # A* and uncertainty-aware A*
  simulation.py    # deterministic synthetic map generator
  evaluation.py    # path-level metrics
experiments/
  run_first_experiment.py
```

Recommended next architecture:

```text
src/uncertainty_navigation/
  core/            # maps, paths, typed states
  planning/        # planner protocol, A*, Dijkstra, risk-aware variants
  evaluation/      # success, collision proxy, risk, path length, runtime
  experiments/     # orchestration helpers
  visualization/   # map and path plotting
  utils/           # config loading, logging, seeds
```

## Performance audit

Current priorities are correctness and reproducibility. Performance should be measured with:

- runtime per map size;
- node expansions;
- memory use for grid representations;
- scaling from small maps to large maps;
- effect of uncertainty penalty on search complexity.

No performance numbers should be reported before scripts generate them.

## Testing audit

Implemented tests now cover:

- A* path recovery on an empty map.
- Structured failure for blocked goals.
- Route change under a high uncertainty penalty.
- Deterministic synthetic map generation.
- Valid start and goal construction.

Required next tests:

- Dijkstra/A* equivalence with admissible heuristic.
- No-path maps.
- Metric computation for failed plans.
- Experiment runner smoke test with a temporary output directory.

## Reproducibility audit

The first experiment runner now saves:

- raw per-trial CSV;
- aggregate summary JSON;
- manifest JSON;
- generated Markdown report.

The next step is to include dependency versions and CI-generated artifacts.

## UX / research presentation audit

The repository now exposes one command for the first experiment. It should next expose one command for figure generation and one command for report aggregation.

## Priority roadmap

| Priority | Improvement | Motivation |
|---:|---|---|
| P0 | Run CI and fix any lint/test failures | Required before merge. |
| P0 | Add experiment runner smoke test | Prevents silent breakage of reproducibility interface. |
| P1 | Add generated uncertainty/path visualizations | Improves research presentation and debugging. |
| P1 | Add benchmark table generator | Encourages honest reporting from raw outputs. |
| P2 | Add planner protocol and Dijkstra baseline | Improves extensibility and baseline fairness. |

## Completed in this hardening pass

- Rewrote README as a research landing page.
- Added this repository audit.
- Added contribution, conduct, security, changelog, Docker, pre-commit, and GitHub template scaffolding.
- Strengthened CI quality gates.
- Added typed grid, planner, simulator, evaluator, deterministic experiment runner, config, and tests.

## Remaining future work

The next scientific milestone is to generate and review first-experiment artifacts, add visualizations, and expand the baseline set without overstating synthetic results.
