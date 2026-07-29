import time
from pathlib import Path
from typing import Optional

import requests  # noqa: E401
from PIL import Image

IMG_OUT = 10


def convert_to_webp(
    image_path: Path, quality: int = 85, delete_original: bool = True
) -> Optional[Path]:
    """Convert image to WebP format."""
    if not image_path or not image_path.exists():
        return None

    webp_path = image_path.with_suffix(".webp")

    if webp_path.exists():
        image_path.unlink()
        return webp_path

    try:
        with Image.open(image_path) as img:
            img.save(webp_path, "WEBP", quality=quality, method=6)

        if delete_original:
            image_path.unlink()

        return webp_path

    except Exception as exc:
        print(f"[ERROR] WebP conversion failed: {exc}")
        return None


def download_image(
    url: str | None,
    filename: str,
    folder: Path,
    retries: int = 3,
    delay: float = 1.0,
    dry_run: bool = False,
) -> Optional[Path]:

    if not url:
        return None

    filepath = folder / filename

    webp_path = filepath.with_suffix(".webp")

    if webp_path.exists() or filepath.exists():
        return filepath

    if dry_run:
        print(f"[DRY-RUN] Download image → {filepath}")
        return filepath

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=IMG_OUT)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)
            return filepath
        except KeyboardInterrupt:
            print("\n[INFO] Received Ctrl+C. Aborting...")
            raise
        except Exception as exc:
            print(f"    [WARN] Image attempt {attempt} failed: {exc}")
            time.sleep(delay)

    return None
