# Cost Function Design

Status: **Research Prototype / Pending Validation**

The experimental planner evaluates a discrete path \(\pi=(x_0,\ldots,x_T)\) using

\[
J(\pi)=\sum_{t=0}^{T-1}\left[c_{distance}(x_t,x_{t+1})+\lambda_u U(x_{t+1})+\lambda_r R(x_{t+1})-\lambda_{rec}Q_{rec}(x_{t+1})+\lambda_{dyn}R_{dyn}(x_{t+1},t)\right].
\]

## Layer definitions and units

- `c_distance`: geometric transition cost, measured in grid-cell units. Four-connected moves currently cost one cell.
- `U`: dimensionless map or belief uncertainty score in `[0, 1]`.
- `R`: dimensionless static navigation-risk score in `[0, 1]`.
- `Q_rec`: dimensionless recoverability score in `[0, 1]`, where larger values indicate better escape or fallback options.
- `R_dyn`: dimensionless predicted dynamic-obstacle risk in `[0, 1]`.
- `lambda_*`: non-negative conversion factors expressed in equivalent grid-cell cost per unit layer score.

## Scale compatibility

Every additive non-geometric layer must be finite and normalized to `[0, 1]` before planning. Without normalization, a layer's numerical scale rather than its scientific meaning determines the selected path. For example, adding raw entropy in bits, clearance in cells, covariance in square metres, and collision scores in one objective makes the weights uninterpretable and scenario dependent.

Validation should reject:

- NaN or infinite values;
- values outside `[0, 1]` beyond a small numerical tolerance;
- negative planner weights;
- a transition cost whose recoverability reward makes the total step cost non-positive.

The current planner uses a positive lower bound on each step cost. This preserves termination but changes the literal objective when the recoverability reward is too large. Experiments must therefore report the applied clipping policy and include an ablation without normalization only as an intentionally invalid control.

## Interpretation of weights

A value `lambda_risk = 4` means traversing a cell with risk `1` incurs four additional grid-cell cost units. It does not imply a fourfold collision probability. Weight interpretation is local to the normalized synthetic model and must not be transferred to physical units without calibration.

## Bounds

For a path of `T` transitions and normalized layers, before positive-cost clipping:

\[
T(1-\lambda_{rec}) \le J(\pi) \le T(1+\lambda_u+\lambda_r+\lambda_{dyn}).
\]

This bound assumes unit four-connected distance cost. If diagonal motion or metric maps are introduced, the geometric lower and upper bounds must be revised.

## Assumptions and limitations

- Layer scores are heuristic unless explicitly calibrated.
- Costs are treated as additive and Markovian, although dynamic risk and localization uncertainty can be temporally correlated.
- The weighted sum represents one scalarization of a multi-objective problem and can miss non-convex Pareto-optimal solutions.
- A normalized score is not automatically a calibrated probability.
- Weight sweeps support sensitivity analysis but cannot establish globally optimal parameters without a justified search domain and independent validation set.
