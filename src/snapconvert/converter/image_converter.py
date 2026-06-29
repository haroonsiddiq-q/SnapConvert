from PIL import Image
from typing import Optional
import io

SUPPORTED_FORMATS = ["jpeg", "png", "webp", "avif"]

# Maps URL-friendly format names to Pillow save format strings
FORMAT_MAP = {
    "jpg":  "jpeg",
    "jpeg": "jpeg",
    "png":  "png",
    "webp": "webp",
    "avif": "avif",
}

# Maps Pillow format to output file extension
EXTENSION_MAP = {
    "jpeg": "jpg",
    "png":  "png",
    "webp": "webp",
    "avif": "avif",
}

# Formats that support a quality setting
QUALITY_FORMATS = {"jpeg", "webp", "avif"}


def convert_image(
    image_bytes: bytes,
    output_format: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale: Optional[float] = None,
    quality: int = 85,
) -> tuple:
    """
    Convert, resize, and/or compress an image.

    Resize priority: width+height > scale > original size.
    Quality only applies to JPEG, WEBP, and AVIF.

    Returns (image_bytes, output_extension).
    """
    fmt = FORMAT_MAP.get(output_format.lower())
    if fmt is None:
        raise ValueError(f"Unsupported format: {output_format}. Choose from: {', '.join(FORMAT_MAP)}")

    if not 1 <= quality <= 95:
        raise ValueError("Quality must be between 1 and 95")

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    # Resize
    if width is not None and height is not None:
        img = img.resize((width, height), Image.LANCZOS)
    elif scale is not None:
        if not 1 <= scale <= 500:
            raise ValueError("Scale must be between 1 and 500 (%)")
        new_width  = max(1, int(img.width  * scale / 100))
        new_height = max(1, int(img.height * scale / 100))
        img = img.resize((new_width, new_height), Image.LANCZOS)

    # JPEG and AVIF don't support alpha — flatten onto white
    if fmt in ("jpeg", "avif"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    else:
        img = img.convert("RGBA")

    buf = io.BytesIO()
    save_kwargs = {"format": fmt}
    if fmt in QUALITY_FORMATS:
        save_kwargs["quality"] = quality

    img.save(buf, **save_kwargs)
    return buf.getvalue(), EXTENSION_MAP[fmt]
