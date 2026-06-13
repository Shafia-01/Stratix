import pytest
from src.data_quality import DataSource

@pytest.mark.unit
def test_data_source_enum_values():
    assert DataSource.LIVE == "live"
    assert DataSource.CACHED == "cached"
    assert DataSource.ESTIMATED == "estimated"
    assert DataSource.UNAVAILABLE == "unavailable"

    assert DataSource.LIVE.value == "live"
    assert isinstance(DataSource.LIVE, str)
