from PIL import Image, ExifTags
import io

SUPPORTED_FORMATS = {"jpeg", "jpg", "png", "webp"}

FORMAT_MAP = {
    "jpg":  "jpeg",
    "jpeg": "jpeg",
    "png":  "png",
    "webp": "webp",
}

EXTENSION_MAP = {
    "jpeg": "jpg",
    "png":  "png",
    "webp": "webp",
}


def read_exif(image_bytes: bytes) -> dict:
    """
    Read and return human-readable EXIF tags from an image.
    Returns an empty dict if no EXIF data is found.
    """
    img = Image.open(io.BytesIO(image_bytes))

    exif_raw = img._getexif() if hasattr(img, "_getexif") else None
    if not exif_raw:
        return {}

    return {
        ExifTags.TAGS.get(tag_id, str(tag_id)): (
            value.decode(errors="replace") if isinstance(value, bytes) else str(value)
        )
        for tag_id, value in exif_raw.items()
    }


def strip_exif(image_bytes: bytes, output_format: str = "jpeg") -> tuple:
    """
    Re-save the image without any EXIF or metadata.

    Pillow drops metadata automatically when saving without passing exif=.
    Returns (image_bytes, output_extension).
    """
    fmt = FORMAT_MAP.get(output_format.lower())
    if fmt is None:
        raise ValueError(
            f"Unsupported format: '{output_format}'. Choose from: {', '.join(FORMAT_MAP)}"
        )

    img = Image.open(io.BytesIO(image_bytes))

    # JPEG doesn't support alpha — flatten onto white if needed
    if fmt == "jpeg" and img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
        img = background
    elif fmt in ("png", "webp"):
        img = img.convert("RGBA")

    buf = io.BytesIO()
    img.save(buf, format=fmt)  # No exif= passed → metadata is dropped
    return buf.getvalue(), EXTENSION_MAP[fmt]
