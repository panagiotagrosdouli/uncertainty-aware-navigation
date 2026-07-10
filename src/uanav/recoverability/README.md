# Recoverability package

This package computes graph-based fallback feasibility over the current occupancy belief and uncertainty map. It is intentionally conservative: cells above occupancy or uncertainty thresholds are excluded from the traversable safe set.

The resulting metrics are analytical proxies for synthetic experiments and must not be interpreted as certified safety guarantees.
