import logging
import time
from pathlib import Path

import requests
from PIL import Image

IMG_OUT = 10
logger = logging.getLogger(__name__)


def get_image_format(image_path: Path) -> str | None:
    """Return the image format (e.g. 'WEBP', 'JPEG', 'PNG')."""

    if not image_path or not image_path.exists():
        return None

    try:
        with Image.open(image_path) as image:
            return image.format

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Unable to determine image format for %s: %s",
            image_path,
            exc,
        )
        return None


def convert_to_webp(
    image_path: Path,
    quality: int = 85,
    delete_original: bool = True,
    overwrite: bool = False,
) -> Path | None:
    """Convert an image to WebP format."""
    if not image_path or not image_path.exists():
        return None
    webp_path = image_path.with_suffix(".webp")
    # WebP already exists
    if webp_path.exists() and not overwrite:
        # Keep the existing WebP and remove the temporary source
        if delete_original and image_path != webp_path:
            image_path.unlink()
            return webp_path
    else:
        # overwrite=True -> remove existing WebP first (may not exist yet)
        webp_path.unlink(missing_ok=True)

    try:
        with Image.open(image_path) as img:
            img.save(
                webp_path,
                "WEBP",
                quality=quality,
                method=6,
            )
        if delete_original and image_path != webp_path:
            image_path.unlink()
            return webp_path
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[ERROR] WebP conversion failed: {exc}")
        return None


def download_image(
    url: str | None,
    filename: str,
    folder: Path,
    retries: int = 3,
    delay: float = 1.0,
    dry_run: bool = False,
) -> str | None:

    if not url:
        return None

    filepath = folder / filename

    logger.debug("Downloading image: %s in to %s", filename, filepath)

    if filepath.exists():
        logger.debug("Image already exists: %s", filename)
        return filename

    if dry_run:
        logger.info(f"[DRY-RUN] Download image → {filepath}")
        return filename

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=IMG_OUT)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)
            logger.info("Saved image: %s", filepath)
            return filename
        except KeyboardInterrupt:
            logger.info("\n[INFO] Received Ctrl+C. Aborting...")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Download attempt %d/%d failed for %s: %s",
                attempt,
                retries,
                filename,
                exc,
            )
            time.sleep(delay)

    return None
