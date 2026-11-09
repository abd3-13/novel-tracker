import pytest
from PIL import Image

from app.utils.images import convert_to_webp

pytestmark = pytest.mark.unit


def test_convert_to_webp_creates_missing_output(tmp_path):
    source = tmp_path / ".cover.jpg"
    Image.new("RGB", (8, 12), "red").save(source, "JPEG")

    result = convert_to_webp(source)

    assert result is not None
    assert result.is_file()
    assert result.suffix == ".webp"
