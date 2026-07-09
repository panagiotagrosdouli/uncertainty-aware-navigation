# Changelog

All notable changes to this project should be documented in this file.

The format follows the spirit of Keep a Changelog, and versioning should follow semantic versioning once releases begin.

## [Unreleased]

### Added

- Research-grade README with scientific positioning, reproducibility policy, limitations, and roadmap.
- Repository audit covering scientific, engineering, documentation, testing, reproducibility, and presentation maturity.
- Contribution guide for research-software development.
- Code of conduct and security policy.
- GitHub issue and pull request templates.
- Dockerfile and pre-commit configuration.
- Stronger CI checks for Ruff, Black, and pytest.
- Typed grid-map, planner-result, and trial-metric data structures.
- Deterministic A*/uncertainty-aware A* planner.
- Synthetic diagnostic grid generator with controlled uncertain and low-uncertainty route alternatives.
- Evaluation metrics for path length, collision proxy, uncertainty exposure, occupancy exposure, obstacle clearance, expanded nodes, runtime, and planner cost.
- Config-driven first-experiment runner that saves raw CSV, aggregate JSON, manifest JSON, and generated Markdown report.
- Unit tests for planner correctness and deterministic simulation.

### Changed

- Clarified that benchmark results are pending until generated through reproducible scripts.
- Clarified the repository's relationship to broader robotics projects on SLAM, VIO, and dynamic navigation.

### Pending

- Generated architecture and pipeline diagrams.
- Plotting scripts for publication-ready heatmaps and path overlays.
- CI artifact upload for generated reports.
- ROS2/Nav2 integration notes after the core static benchmark stabilizes.
