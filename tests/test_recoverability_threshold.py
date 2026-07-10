import numpy as np

from uanav.recoverability import assess_path_recoverability


def test_recoverability_threshold_can_reject_narrow_route() -> None:
    probability = np.full((7, 7), 0.95)
    uncertainty = np.zeros_like(probability)
    probability[3, 1:6] = 0.1

    assessment = assess_path_recoverability(
        "narrow-route",
        [(3, 2), (3, 3), (3, 4)],
        probability,
        uncertainty,
        safe_regions={(3, 1)},
        recoverability_threshold=0.8,
    )

    assert not assessment.admissible
    assert assessment.fallback_path_exists
    assert assessment.rejection_reason is not None
    assert "below the required threshold" in assessment.rejection_reason
