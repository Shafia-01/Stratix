# scoring.py
def compute_score(volume: float, competition: float, cpc: float) -> float:
    """
    Compute a composite SEO score combining volume, competition, and CPC.
    The higher the score, the more rankable and valuable the keyword is.
    
    - volume: average monthly search volume
    - competition: between 0 (low) and 1 (high)
    - cpc: cost per click (in USD)
    """
    try:
        vol_norm = min(volume / 10000, 1.0)
        comp_norm = max(0, min(competition, 1.0))
        cpc_norm = min(cpc / 10, 1.0)

        score = (0.6 * vol_norm) + (0.3 * (1 - comp_norm)) + (0.1 * (1 - cpc_norm))
        return round(score, 3)
    except Exception as e:
        print(f"⚠️ Score computation error: {e}")
        return 0.0
