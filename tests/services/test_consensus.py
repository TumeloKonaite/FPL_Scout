from src.services.consensus import (
    MODERATE_CONSENSUS_THRESHOLD,
    STRONG_CONSENSUS_THRESHOLD,
    consensus_level,
    support_ratio,
)


def test_consensus_thresholds_are_centralized_and_inclusive() -> None:
    assert STRONG_CONSENSUS_THRESHOLD == 0.70
    assert MODERATE_CONSENSUS_THRESHOLD == 0.50
    assert consensus_level(7, 10) == "strong"
    assert consensus_level(5, 10) == "moderate"
    assert consensus_level(4, 10) == "split"


def test_consensus_safely_handles_unknown_expert_total() -> None:
    assert support_ratio(0, 0) is None
    assert consensus_level(0, 0) == "split"

