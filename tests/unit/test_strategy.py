import pytest

from app.constants import SyncMode
from app.sync.strategy import SyncStrategy

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        [],
        {},
        (),
    ],
)
def test_is_empty(value):
    assert SyncStrategy.is_empty(value) is True


@pytest.mark.parametrize(
    "value",
    [
        0,
        False,
        "0",
        [0],
        {"value": 0},
        (0,),
    ],
)
def test_is_not_empty(value):
    assert SyncStrategy.is_empty(value) is False


def test_overwrite_always_updates():
    assert (
        SyncStrategy.should_update(
            SyncMode.OVERWRITE,
            "old",
            "new",
        )
        is True
    )


def test_overwrite_updates_even_when_current_is_empty():
    assert (
        SyncStrategy.should_update(
            SyncMode.OVERWRITE,
            None,
            "new",
        )
        is True
    )


@pytest.mark.parametrize(
    "mode",
    [
        SyncMode.FILL_MISSING,
        SyncMode.SKIP_EXISTING,
    ],
)
def test_missing_modes_update_empty_values(mode):
    assert (
        SyncStrategy.should_update(
            mode,
            None,
            "new",
        )
        is True
    )

    assert (
        SyncStrategy.should_update(
            mode,
            "",
            "new",
        )
        is True
    )


@pytest.mark.parametrize(
    "mode",
    [
        SyncMode.FILL_MISSING,
        SyncMode.SKIP_EXISTING,
    ],
)
def test_missing_modes_do_not_update_existing_values(mode):
    assert (
        SyncStrategy.should_update(
            mode,
            "old",
            "new",
        )
        is False
    )


def test_only_changed_updates_when_values_differ():
    assert (
        SyncStrategy.should_update(
            SyncMode.ONLY_CHANGED,
            "old",
            "new",
        )
        is True
    )


def test_only_changed_skips_identical_values():
    assert (
        SyncStrategy.should_update(
            SyncMode.ONLY_CHANGED,
            "same",
            "same",
        )
        is False
    )


@pytest.mark.parametrize(
    "mode",
    [
        SyncMode.OVERWRITE,
        SyncMode.FILL_MISSING,
        SyncMode.SKIP_EXISTING,
        SyncMode.ONLY_CHANGED,
    ],
)
def test_none_new_value_never_updates(mode):
    assert (
        SyncStrategy.should_update(
            mode,
            "current",
            None,
        )
        is False
    )


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="Unknown sync mode"):
        SyncStrategy.should_update(
            "invalid",
            "old",
            "new",
        )
