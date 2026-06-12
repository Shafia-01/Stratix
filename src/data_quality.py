from enum import Enum

class DataSource(str, Enum):
    LIVE = "live"            # real API data
    CACHED = "cached"         # real data, served from DB cache
    ESTIMATED = "estimated"   # deterministic heuristic, NOT random
    UNAVAILABLE = "unavailable"  # no data could be obtained
