from PIL import Image
import io
import re

def apply_background_color(image_bytes: bytes, hex_color: str = "#ffffff") -> bytes:
    hex_color = hex_color.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", hex_color):
        raise ValueError(f"Invalid hex color: #{hex_color}")

    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    foreground = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    background = Image.new("RGBA", foreground.size, (r, g, b, 255))
    background.paste(foreground, mask=foreground.split()[3])

    buf = io.BytesIO()
    background.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
