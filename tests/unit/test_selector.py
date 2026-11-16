import pytest

from app.sync.selector import BulkSelector

pytestmark = pytest.mark.unit


def test_selector_includes_nsfw_by_default():
    assert "LOWER(tags)" not in BulkSelector(table="novels")._select


def test_selector_hides_nsfw_when_requested():
    query = BulkSelector(table="novels", include_nsfw=False)._select

    assert "tags IS NULL" in query
    assert "LOWER(tags) NOT LIKE '%nsfw%'" in query
