import numpy as np

from uanav.recoverability import assess_path_recoverability


def test_empty_path_is_explicitly_rejected() -> None:
    probability = np.full((3, 3), 0.1)
    uncertainty = np.zeros_like(probability)

    assessment = assess_path_recoverability(
        "empty",
        [],
        probability,
        uncertainty,
        safe_regions={(1, 1)},
    )

    assert not assessment.admissible
    assert assessment.first_irrecoverable_index == 0
    assert assessment.rejection_reason == "Candidate path is empty."


def test_high_uncertainty_breaks_safe_set_connectivity() -> None:
    probability = np.full((5, 5), 0.1)
    uncertainty = np.zeros_like(probability)
    uncertainty[:, 2] = 0.95

    assessment = assess_path_recoverability(
        "uncertain-barrier",
        [(2, 1), (2, 2), (2, 3)],
        probability,
        uncertainty,
        safe_regions={(2, 1)},
        recoverability_threshold=0.0,
    )

    assert not assessment.admissible
    assert assessment.first_irrecoverable_index == 1
    assert assessment.rejection_reason == "Fallback path is lost at candidate index 1."
