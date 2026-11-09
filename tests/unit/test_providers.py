from types import SimpleNamespace

import pytest

from app.constants import MetadataKey
from app.sync import providers as providers_module
from app.sync.providers import LocalProvider

pytestmark = pytest.mark.unit


def load_local_provider(monkeypatch, tmp_path, novel):
    monkeypatch.setattr(providers_module.db, "get_value", lambda key: str(tmp_path))

    warnings = []
    logger = SimpleNamespace(debug=lambda *_: None, warning=warnings.append)
    ctx = SimpleNamespace(novel=novel, logger=logger, emit=lambda *_, **__: None)

    provider = LocalProvider(ctx)
    provider.load()

    return provider, warnings


def test_local_provider_marks_missing_epub_as_not_existing(monkeypatch, tmp_path):
    provider, warnings = load_local_provider(
        monkeypatch,
        tmp_path,
        {
            MetadataKey.ID: 1,
            MetadataKey.TITLE: "Missing Book",
            MetadataKey.FILEPATH: "missing.epub",
        },
    )

    assert provider.get(MetadataKey.EPUB_EXISTS) is False
    assert provider.get(MetadataKey.FILEPATH) == "missing.epub"
    assert provider.get(MetadataKey.TITLE) is None
    assert any("EPUB file not found" in message for message in warnings)


def test_local_provider_marks_novel_without_filepath_as_not_existing(
    monkeypatch, tmp_path
):
    provider, _ = load_local_provider(
        monkeypatch,
        tmp_path,
        {
            MetadataKey.ID: 2,
            MetadataKey.TITLE: "No File",
            MetadataKey.FILEPATH: None,
        },
    )

    assert provider.get(MetadataKey.EPUB_EXISTS) is False
