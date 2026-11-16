import pytest

from app.routes.main import validate_novel_updates

pytestmark = pytest.mark.unit


def test_validate_novel_updates_coerces_numbers_and_booleans():
    updates = validate_novel_updates(
        {
            "localchap": "12",
            "progress": 4,
            "epub_exists": True,
            "name": "Book",
        }
    )

    assert updates == {
        "localchap": 12,
        "progress": 4,
        "epub_exists": 1,
        "name": "Book",
    }


def test_validate_novel_updates_accepts_checkbox_strings():
    assert validate_novel_updates({"epub_exists": "0"}) == {"epub_exists": 0}
    assert validate_novel_updates({"epub_exists": "1"}) == {"epub_exists": 1}


def test_validate_novel_updates_ignores_unknown_fields():
    assert validate_novel_updates({"not_a_column": "value"}) == {}


@pytest.mark.parametrize(
    "payload",
    [
        {"localchap": "many"},
        {"localchap": True},
        {"progress": -1},
        {"name": ""},
        {"name": None},
        {"author": ["not", "text"]},
        {"epub_exists": "maybe"},
    ],
)
def test_validate_novel_updates_rejects_invalid_values(payload):
    with pytest.raises(ValueError):
        validate_novel_updates(payload)


def test_validate_novel_updates_allows_null_text_fields():
    assert validate_novel_updates({"author": None}) == {"author": None}
