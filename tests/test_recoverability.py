import numpy as np

from uanav.recoverability import assess_path_recoverability, reachable_safe_set


def test_reachable_safe_set_excludes_blocked_component() -> None:
    probability = np.full((5, 7), 0.1)
    uncertainty = np.zeros_like(probability)
    probability[:, 3] = 0.95

    safe_set = reachable_safe_set(probability, uncertainty, {(2, 1)})

    assert safe_set[2, 1]
    assert safe_set[2, 2]
    assert not safe_set[2, 4]


def test_recoverability_rejects_path_after_fallback_is_lost() -> None:
    probability = np.full((5, 7), 0.1)
    uncertainty = np.zeros_like(probability)
    probability[:, 3] = 0.95
    path = [(2, 1), (2, 2), (2, 3), (2, 4)]

    assessment = assess_path_recoverability(
        "blocked-crossing",
        path,
        probability,
        uncertainty,
        safe_regions={(2, 1)},
        recoverability_threshold=0.0,
    )

    assert not assessment.admissible
    assert not assessment.fallback_path_exists
    assert assessment.first_irrecoverable_index == 2
    assert assessment.rejection_reason == "Fallback path is lost at candidate index 2."


def test_recoverability_accepts_redundant_safe_path() -> None:
    probability = np.full((7, 7), 0.1)
    uncertainty = np.zeros_like(probability)
    path = [(3, 3), (3, 4), (3, 5)]

    assessment = assess_path_recoverability(
        "open-route",
        path,
        probability,
        uncertainty,
        safe_regions={(3, 1)},
        recoverability_threshold=0.45,
    )

    assert assessment.admissible
    assert assessment.fallback_path_exists
    assert assessment.escape_route_count >= 3
    assert assessment.route_redundancy == 1.0
    assert assessment.minimum_future_clearance > 1.0
