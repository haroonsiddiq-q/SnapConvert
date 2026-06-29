from PIL import Image
import io

FLIP_DIRECTIONS = ["horizontal", "vertical"]


def _to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def rotate_image(
    image_bytes: bytes,
    degrees: float,
    expand: bool = True,
) -> bytes:
    """
    Rotate image by degrees (counter-clockwise).

    expand=True grows the canvas to fit the full rotated image.
    expand=False keeps the original canvas size, cropping the corners.
    Preserves transparency (RGBA).
    """
    if degrees == 0:
        return _to_png(Image.open(io.BytesIO(image_bytes)))

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    rotated = img.rotate(degrees, expand=expand, resample=Image.BICUBIC)
    return _to_png(rotated)


def flip_image(
    image_bytes: bytes,
    direction: str,
) -> bytes:
    """
    Flip image horizontally or vertically.

    direction: 'horizontal' (mirror left-right) or 'vertical' (mirror top-bottom).
    """
    direction = direction.lower()
    if direction not in FLIP_DIRECTIONS:
        raise ValueError(f"Invalid direction '{direction}'. Choose from: {', '.join(FLIP_DIRECTIONS)}")

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    if direction == "horizontal":
        result = img.transpose(Image.FLIP_LEFT_RIGHT)
    else:
        result = img.transpose(Image.FLIP_TOP_BOTTOM)

    return _to_png(result)
