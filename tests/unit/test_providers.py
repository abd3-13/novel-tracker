from types import SimpleNamespace

import pytest

from app.constants import MetadataKey
from app.sync import providers as providers_module
from app.sync.providers import LocalProvider
from app.sync.webnovel.api import NovelInfo

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


def online_context(novel, tmp_path, monkeypatch):
    monkeypatch.setattr(providers_module.db, "get_value", lambda key: str(tmp_path))

    collected = {"debug": [], "info": [], "warning": [], "error": []}
    logger = SimpleNamespace(
        **{name: collected[name].append for name in collected}
    )
    ctx = SimpleNamespace(novel=novel, logger=logger, emit=lambda *_, **__: None)

    return providers_module.OnlineProvider(ctx), collected


def online_novel():
    return {
        MetadataKey.ID: 1,
        MetadataKey.TITLE: "Online Book",
        MetadataKey.FILEPATH: "online.epub",
        MetadataKey.URL: "https://example.test/book_12345678",
        MetadataKey.SOURCE: "webnovel",
    }


def test_character_service_failure_is_reported_as_an_error(monkeypatch, tmp_path):
    def failing(**_kwargs):
        raise providers_module.CharacterServiceError("service unavailable")

    monkeypatch.setattr(providers_module, "WN_fetch_characters", failing)

    provider, collected = online_context(online_novel(), tmp_path, monkeypatch)

    assert provider.fetch_characters() is None
    assert any("service unavailable" in message for message in collected["error"])


def test_partial_character_failure_is_reported_as_a_warning(monkeypatch, tmp_path):
    monkeypatch.setattr(
        providers_module,
        "WN_fetch_characters",
        lambda **_kwargs: {"characters": 2, "failed": 1},
    )

    provider, collected = online_context(online_novel(), tmp_path, monkeypatch)

    assert provider.fetch_characters() == {"characters": 2, "failed": 1}
    assert any("1 failed" in message for message in collected["warning"])


def test_cover_failure_is_reported_as_a_warning(monkeypatch, tmp_path):
    monkeypatch.setattr(
        providers_module._client, "fetch_cover_image", lambda *_, **__: None
    )

    provider, collected = online_context(online_novel(), tmp_path, monkeypatch)

    assert provider.fetch_cover() is None
    assert any("cover" in message.lower() for message in collected["warning"])


def test_character_count_failure_keeps_the_rest_of_the_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(
        providers_module._client,
        "fetch_latest_chapter",
        lambda book_id: NovelInfo(
            chapter=10,
            chapter_time=None,
            author="Author",
            description="Description",
            status="Ongoing",
            title="Online Book",
            cover="12345678.webp",
        ),
    )
    monkeypatch.setattr(
        providers_module._client,
        "count_online_characters",
        lambda book_id: (_ for _ in ()).throw(RuntimeError("rate limited")),
    )

    provider, collected = online_context(online_novel(), tmp_path, monkeypatch)
    provider.load()

    assert provider.get(MetadataKey.TITLE) == "Online Book"
    assert provider.get(MetadataKey.ONLINE_CHAPTERS) == 10
    assert provider.get(MetadataKey.ONLINE_CHARACTERS) is None
    assert any("rate limited" in message for message in collected["warning"])
