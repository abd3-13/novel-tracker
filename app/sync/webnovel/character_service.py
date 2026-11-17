from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.constants import (
    WebnovelErrorMessage,
    WebnovelSummaryKey,
    WebnovelSummaryStatus,
)
from app.utils.tools import (
    write_characters_json,
    write_characters_txt,
)

from .api import CharacterInfo, WebnovelClient

logger = logging.getLogger(__name__)
_client = WebnovelClient()


# Number of retries for failed detail fetches.
MAX_RETRY = 5


class CharacterServiceError(Exception):
    """Base exception for the character service."""


class CharacterFetchError(CharacterServiceError):
    """Raised when characters cannot be fetched."""


@dataclass(slots=True)
class CharacterTask:
    """
    Internal representation of one character.
    This class is never exposed outside the service.
    """

    role_id: str
    name: str
    detail_failed: bool = False


@dataclass(slots=True)
class CharacterFetchState:
    """
    Internal working state.
    Shared between the private helper functions.
    """

    book_id: str
    output_dir: Path
    dry_run: bool
    tasks: list[CharacterTask] = field(default_factory=list)
    characters: list[CharacterInfo] = field(default_factory=list)


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------


def fetch_characters(
    *,
    book_id: str | None = None,
    output_dir: Path,
    dry_run: bool = False,
) -> dict:
    """
    Fetch all WebNovel characters.
    Workflow
      Character list > Character details > Retry failed details > Write JSON/TXT > Return summary
    """
    if not book_id:
        raise CharacterFetchError(WebnovelErrorMessage.BOOK_ID_REQUIRED)

    logger.info("Initializing character fetch...")
    output_dir = Path(output_dir)
    if output_dir.suffix:
        output_dir = output_dir.with_suffix("")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Character output directory: %s", output_dir)

    state = CharacterFetchState(
        book_id=book_id,
        output_dir=output_dir,
        dry_run=dry_run,
    )
    logger.info("Loading character list...")
    _load_character_list(state)
    logger.info("Fetching character details...")
    _fetch_character_details(state)
    logger.info("Retrying failed details...")
    _retry_failed_details(state)
    if not dry_run:
        logger.info("Writing output files...")
        _write_outputs(state)
    return _build_summary(state)


# ----------------------------------------------------------------------
# Step 1
# ----------------------------------------------------------------------
def _load_character_list(state: CharacterFetchState) -> None:
    "Retrieve the list of characters from WebNovel."
    try:
        items = _client.get_character_list(state.book_id)
    except Exception as exc:  # noqa: BLE001
        raise CharacterFetchError(
            f"Could not load characters for book {state.book_id}: {exc}"
        ) from exc

    if not items:
        raise CharacterFetchError(
            WebnovelErrorMessage.NO_CHARACTER_LIST.format(book_id=state.book_id)
        )

    for item in items:
        state.tasks.append(CharacterTask(role_id=item.role_id, name=item.name))


# ----------------------------------------------------------------------
# Step 2
# ----------------------------------------------------------------------
def _fetch_character_details(state: CharacterFetchState) -> None:
    """
    Fetch details once.
    Failed requests are marked for retry.
    """
    for task in state.tasks:
        try:
            detail = _client.get_character_detail(state.book_id, task.role_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Character detail failed for %s (%s): %s",
                task.name,
                task.role_id,
                exc,
            )
            task.detail_failed = True
            continue

        if detail is None:
            task.detail_failed = True
            continue

        state.characters.append(detail)


# ----------------------------------------------------------------------
# Step 3
# ----------------------------------------------------------------------
def _retry_failed_details(state: CharacterFetchState) -> None:
    """
    Retry failed detail requests.
    """
    for task in state.tasks:
        if not task.detail_failed:
            continue
        for _ in range(MAX_RETRY):
            try:
                detail = _client.get_character_detail(state.book_id, task.role_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Character detail retry failed for %s (%s): %s",
                    task.name,
                    task.role_id,
                    exc,
                )
                continue
            if detail is None:
                continue
            task.detail_failed = False
            state.characters.append(detail)
            break


# ----------------------------------------------------------------------
# Step 4
# ----------------------------------------------------------------------
def _write_outputs(
    state: CharacterFetchState,
) -> None:
    """
    Write all output files.
    """
    characters_dict = [asdict(character) for character in state.characters]
    write_characters_json(characters_dict, state.output_dir)
    write_characters_txt(characters_dict, state.output_dir)


# ----------------------------------------------------------------------
# Step 5
# ----------------------------------------------------------------------
def _build_summary(state: CharacterFetchState) -> dict:
    """
    Build the Flask/CLI response.
    """
    failed = sum(1 for task in state.tasks if task.detail_failed)
    return {
        WebnovelSummaryKey.STATUS: (
            WebnovelSummaryStatus.SUCCESS
            if failed == 0
            else WebnovelSummaryStatus.PARTIAL
        ),
        WebnovelSummaryKey.BOOK_ID: state.book_id,
        WebnovelSummaryKey.CHARACTERS: len(state.characters),
        WebnovelSummaryKey.FAILED: failed,
        WebnovelSummaryKey.OUTPUT_DIR: str(state.output_dir),
        WebnovelSummaryKey.MSG: (
            f"Fetched {len(state.characters)} of {len(state.tasks)} characters"
        ),
    }
