def compute_score(volume, competition, cpc):
    norm_volume = min(volume / 10000, 1)
    norm_competition = competition
    return round(0.6 * norm_volume + 0.35 * (1 - norm_competition) + 0.05 * (1 - cpc), 3)
