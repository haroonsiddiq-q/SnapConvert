from PIL import Image
from rembg import remove, new_session
from functools import lru_cache
import io


@lru_cache(maxsize=None)
def _get_session(model: str):
    return new_session(model)


def _to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def crop_manual(
    image_bytes: bytes,
    x: int,
    y: int,
    width: int,
    height: int,
) -> bytes:
    """
    Crop image to an exact region.

    (x, y) is the top-left corner.
    Raises ValueError if the crop box exceeds the image bounds.
    """
    img = Image.open(io.BytesIO(image_bytes))
    img_w, img_h = img.size

    if x < 0 or y < 0:
        raise ValueError("x and y must be 0 or greater")
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be greater than 0")
    if x + width > img_w or y + height > img_h:
        raise ValueError(
            f"Crop box ({x},{y},{x+width},{y+height}) exceeds image size ({img_w}x{img_h})"
        )

    cropped = img.crop((x, y, x + width, y + height))
    return _to_png(cropped)


def crop_smart(
    image_bytes: bytes,
    padding: int = 10,
    model: str = "u2net",
) -> bytes:
    """
    Auto-crop to the subject's bounding box.

    Uses rembg to find the subject mask, derives the bounding box
    from the alpha channel, then crops the ORIGINAL image to those bounds.
    The background is preserved — only the canvas is tightened.
    """
    if padding < 0:
        raise ValueError("Padding must be 0 or greater")

    original = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    img_w, img_h = original.size

    # Get alpha mask from rembg — we only use this to find subject bounds
    session = _get_session(model)
    mask_result = remove(original, session=session, only_mask=True)
    mask = mask_result.convert("L")

    # Find bounding box of non-zero (subject) pixels in the mask
    bbox = mask.getbbox()
    if bbox is None:
        # No subject found — return original unchanged
        return _to_png(original)

    x1, y1, x2, y2 = bbox

    # Apply padding, clamped to image bounds
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(img_w, x2 + padding)
    y2 = min(img_h, y2 + padding)

    cropped = original.crop((x1, y1, x2, y2))
    return _to_png(cropped)
