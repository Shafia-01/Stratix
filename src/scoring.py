def compute_score(volume, competition, cpc):
    """
    Compute a composite SEO score combining volume, competition, and CPC.
    The higher the score, the more rankable and valuable the keyword is.
    """
    # Normalize metrics
    vol_norm = min(volume / 10000, 1.0)
    comp_norm = competition
    cpc_norm = min(cpc / 10, 1.0)

    # Weighted score
    score = (0.6 * vol_norm) + (0.3 * (1 - comp_norm)) + (0.1 * (1 - cpc_norm))
    return round(score, 3)
