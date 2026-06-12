from src.logger_config import get_logger

logger = get_logger(__name__)

def compute_score(metrics: dict, mode: str = "standard") -> float:
    """
    Compute a composite SEO opportunity score from volume, CPC, and competition.
    mode="standard": weights used by the full research agent.
    mode="lightweight": weights used by the lightweight/quick agent.
    Returns 0.0 if required metrics are missing/unavailable (data_source="unavailable").
    """
    # TODO(Phase 2+): reconcile standard vs lightweight scoring formulas into one
    try:
        volume = metrics.get("volume") or 0
        cpc = metrics.get("cpc") or 0
        competition = metrics.get("competition")
        
        # If competition data is unavailable, assume neutral 0.5
        if competition is None:
            competition = 0.5

        if mode == "lightweight":
            score = (volume * 0.4 + cpc * 50 * 0.3 + (1 - competition) * 50 * 0.3) / 100
        else:
            score = (volume * 0.5 + cpc * 100 * 0.3 + (1 - competition) * 100 * 0.2) / 100
            
        return round(score, 3)
    except Exception as e:
        logger.exception("Score computation error")
        return 0.0

def classify_difficulty(score: float, mode: str = "standard") -> str:
    """
    Classify keyword difficulty based on the computed opportunity score.
    """
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
