"""
SEO keyword opportunity scoring for Keylytics.

compute_score() returns an OpportunityScore instance (not a bare float) so
callers have the full breakdown (score, difficulty, mode, inputs) in one object.
classify_difficulty() is retained as a standalone helper for cases where
only the label is needed without constructing a full OpportunityScore.
"""

from src.logger_config import get_logger
from src.schemas import OpportunityScore

logger = get_logger(__name__)


def compute_score(metrics: dict, mode: str = "standard") -> OpportunityScore:
    """
    Compute a composite SEO opportunity score from volume, CPC, and competition.

    mode="standard":    weights used by the full research agent.
    mode="lightweight": weights used by the lightweight/quick agent.

    Returns an OpportunityScore instance (score=0.0, difficulty="Hard" on error).
    Returns score=0.0 when required metrics are missing / data_source="unavailable".
    """
    # TODO(Phase 2+): reconcile standard vs lightweight scoring formulas into one
    volume = float(metrics.get("volume") or 0)
    cpc = float(metrics.get("cpc") or 0)
    competition = metrics.get("competition")

    # If competition data is unavailable, assume neutral 0.5
    if competition is None:
        competition = 0.5
    competition = float(competition)

    try:
        if mode == "lightweight":
            raw = (volume * 0.4 + cpc * 50 * 0.3 + (1 - competition) * 50 * 0.3) / 100
        else:
            raw = (volume * 0.5 + cpc * 100 * 0.3 + (1 - competition) * 100 * 0.2) / 100

        score = round(max(0.0, raw), 3)
    except Exception:
        logger.exception("Score computation error")
        score = 0.0

    difficulty = classify_difficulty(score, mode)

    return OpportunityScore(
        score=score,
        difficulty=difficulty,
        mode=mode,
        volume=volume,
        cpc=cpc if cpc != 0 else None,
        competition=competition,
    )


def classify_difficulty(score: float, mode: str = "standard") -> str:
    """
    Classify keyword difficulty based on the computed opportunity score.
    Accepts either a raw float or an OpportunityScore instance.
    """
    # Accept OpportunityScore instances transparently
    if hasattr(score, "score"):
        score = score.score

    if mode == "lightweight":
        if score >= 0.7:
            return "Easy"
        elif score >= 0.4:
            return "Medium"
        return "Hard"

    # Standard thresholds
    if score >= 0.8:
        return "Easy"
    elif score >= 0.5:
        return "Medium"
    return "Hard"
