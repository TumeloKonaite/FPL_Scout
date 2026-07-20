from __future__ import annotations

from typing import Literal


ConsensusLevel = Literal["strong", "moderate", "split"]

# Keep product language and thresholds in one place so API and UI behavior can
# evolve without embedding policy in each recommendation category.
STRONG_CONSENSUS_THRESHOLD = 0.70
MODERATE_CONSENSUS_THRESHOLD = 0.50


def support_ratio(support_count: int, relevant_expert_count: int) -> float | None:
    if relevant_expert_count <= 0:
        return None
    return round(support_count / relevant_expert_count, 4)


def consensus_level(
    support_count: int,
    relevant_expert_count: int,
) -> ConsensusLevel:
    ratio = support_ratio(support_count, relevant_expert_count)
    if ratio is not None and ratio >= STRONG_CONSENSUS_THRESHOLD:
        return "strong"
    if ratio is not None and ratio >= MODERATE_CONSENSUS_THRESHOLD:
        return "moderate"
    return "split"
