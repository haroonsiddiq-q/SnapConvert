from PIL import Image, ImageEnhance
import io


def _to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _validate(value: float, name: str) -> None:
    if value < 0.0:
        raise ValueError(f"'{name}' must be 0.0 or greater (got {value})")


def apply_filters(
    image_bytes: bytes,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    sharpness: float = 1.0,
) -> bytes:
    """
    Apply brightness, contrast, saturation, and sharpness adjustments.

    All values are multipliers where:
      1.0 = original
      0.0 = none (black for brightness/contrast, greyscale for saturation, blurred for sharpness)
      2.0 = double

    Preserves transparency (RGBA).
    """
    for value, name in [
        (brightness, "brightness"),
        (contrast,   "contrast"),
        (saturation, "saturation"),
        (sharpness,  "sharpness"),
    ]:
        _validate(value, name)

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    # Split alpha — ImageEnhance doesn't handle RGBA safely for all enhancers
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))

    rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    rgb = ImageEnhance.Color(rgb).enhance(saturation)
    rgb = ImageEnhance.Sharpness(rgb).enhance(sharpness)

    # Reattach alpha
    r2, g2, b2 = rgb.split()
    result = Image.merge("RGBA", (r2, g2, b2, a))
    return _to_png(result)
