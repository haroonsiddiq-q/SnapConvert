from PIL import Image, ImageDraw, ImageFont
import io
from typing import Optional

POSITIONS = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
MARGIN = 20


def _to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _parse_hex_color(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _get_position(
    canvas_w: int,
    canvas_h: int,
    item_w: int,
    item_h: int,
    position: str,
) -> tuple:
    """Calculate top-left (x, y) for placing an item at a named position."""
    if position == "top-left":
        return (MARGIN, MARGIN)
    elif position == "top-right":
        return (canvas_w - item_w - MARGIN, MARGIN)
    elif position == "bottom-left":
        return (MARGIN, canvas_h - item_h - MARGIN)
    elif position == "bottom-right":
        return (canvas_w - item_w - MARGIN, canvas_h - item_h - MARGIN)
    elif position == "center":
        return ((canvas_w - item_w) // 2, (canvas_h - item_h) // 2)
    else:
        raise ValueError(f"Invalid position '{position}'. Choose from: {', '.join(POSITIONS)}")


def watermark_text(
    image_bytes: bytes,
    text: str,
    position: str = "bottom-right",
    font_size: int = 36,
    color: str = "#ffffff",
    opacity: int = 70,
) -> bytes:
    """
    Overlay text onto an image.

    position: top-left, top-right, bottom-left, bottom-right, center.
    color:    Hex color string e.g. #ffffff.
    opacity:  0–100 percent.
    """
    if not text.strip():
        raise ValueError("Text cannot be empty")
    if position not in POSITIONS:
        raise ValueError(f"Invalid position '{position}'. Choose from: {', '.join(POSITIONS)}")
    if not 0 <= opacity <= 100:
        raise ValueError("Opacity must be between 0 and 100")
    if font_size < 1:
        raise ValueError("font_size must be at least 1")

    r, g, b = _parse_hex_color(color)
    alpha = int(opacity / 100 * 255)

    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    txt_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x, y = _get_position(base.width, base.height, text_w, text_h, position)
    draw.text((x, y), text, font=font, fill=(r, g, b, alpha))

    result = Image.alpha_composite(base, txt_layer)
    return _to_png(result)


def watermark_image(
    image_bytes: bytes,
    watermark_bytes: bytes,
    position: str = "bottom-right",
    scale: int = 20,
    opacity: int = 70,
) -> bytes:
    """
    Overlay an image (logo) onto a base image.

    position: top-left, top-right, bottom-left, bottom-right, center.
    scale:    Watermark width as % of base image width (1–100).
    opacity:  0–100 percent.
    """
    if position not in POSITIONS:
        raise ValueError(f"Invalid position '{position}'. Choose from: {', '.join(POSITIONS)}")
    if not 1 <= scale <= 100:
        raise ValueError("Scale must be between 1 and 100")
    if not 0 <= opacity <= 100:
        raise ValueError("Opacity must be between 0 and 100")

    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    wm   = Image.open(io.BytesIO(watermark_bytes)).convert("RGBA")

    # Scale watermark relative to base image width
    target_w = max(1, int(base.width * scale / 100))
    ratio    = target_w / wm.width
    target_h = max(1, int(wm.height * ratio))
    wm = wm.resize((target_w, target_h), Image.LANCZOS)

    # Apply opacity to watermark alpha channel
    if opacity < 100:
        r, g, b, a = wm.split()
        a = a.point(lambda v: int(v * opacity / 100))
        wm = Image.merge("RGBA", (r, g, b, a))

    x, y = _get_position(base.width, base.height, wm.width, wm.height, position)

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay.paste(wm, (x, y))
    result = Image.alpha_composite(base, overlay)
    return _to_png(result)
