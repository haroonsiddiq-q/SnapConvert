from PIL import Image, ImageOps
import io

def replace_background(foreground_bytes: bytes, background_bytes: bytes) -> bytes:
    foreground = Image.open(io.BytesIO(foreground_bytes)).convert("RGBA")
    background = Image.open(io.BytesIO(background_bytes)).convert("RGBA")

    background = ImageOps.fit(background, foreground.size)

    background.paste(foreground, mask=foreground.split()[3])

    buf = io.BytesIO()
    background.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
