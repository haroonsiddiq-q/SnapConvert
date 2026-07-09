from PIL import Image, ImageEnhance
import io
import math
import random

PIXELATE_METHODS = ["nearest", "palette"]
ANIMATE_EFFECTS = ["bob", "shimmer", "glow"]


def _pixelate_nearest(img: Image.Image, pixel_size: int) -> Image.Image:
    small_w = max(1, img.width // pixel_size)
    small_h = max(1, img.height // pixel_size)
    small = img.resize((small_w, small_h), Image.NEAREST)
    return small.resize((img.width, img.height), Image.NEAREST)


def pixelate_image(
    image_bytes: bytes,
    pixel_size: int = 16,
    palette_colors: int = 0,
    method: str = "nearest",
) -> bytes:
    if pixel_size < 1:
        raise ValueError(f"'pixel_size' must be 1 or greater (got {pixel_size})")
    if palette_colors < 0 or palette_colors > 256:
        raise ValueError(f"'palette_colors' must be between 0 and 256 (got {palette_colors})")
    if method not in PIXELATE_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose from: {', '.join(PIXELATE_METHODS)}")

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    if method == "palette" and palette_colors == 0:
        palette_colors = 32

    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))

    rgb = _pixelate_nearest(rgb, pixel_size)

    if palette_colors > 0:
        rgb = rgb.convert("P", palette=Image.ADAPTIVE, colors=palette_colors).convert("RGB")

    r2, g2, b2 = rgb.split()
    result = Image.merge("RGBA", (r2, g2, b2, a))

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()


def _bob_frame(rgba: Image.Image, offset_px: int) -> Image.Image:
    frame = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    frame.paste(rgba, (0, offset_px))
    return frame


def _shimmer_frame(rgb: Image.Image, seed: int, strength: int) -> Image.Image:
    rnd = random.Random(seed)
    px = rgb.load()
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            if rnd.random() < 0.15:
                r, g, b = px[x, y]
                delta = rnd.randint(-strength, strength)
                px[x, y] = (
                    max(0, min(255, r + delta)),
                    max(0, min(255, g + delta)),
                    max(0, min(255, b + delta)),
                )
    return rgb


def _glow_frame(rgb: Image.Image, factor: float) -> Image.Image:
    return ImageEnhance.Brightness(rgb).enhance(factor)


def pixelate_to_gif(
    image_bytes: bytes,
    pixel_size: int = 16,
    palette_colors: int = 32,
    effect: str = "bob",
    frame_count: int = 8,
    frame_duration_ms: int = 120,
    intensity: int = 3,
) -> bytes:
    if frame_count < 2:
        raise ValueError(f"'frame_count' must be 2 or greater (got {frame_count})")
    if effect not in ANIMATE_EFFECTS:
        raise ValueError(f"Invalid effect '{effect}'. Choose from: {', '.join(ANIMATE_EFFECTS)}")

    base_png = pixelate_image(
        image_bytes, pixel_size=pixel_size, palette_colors=palette_colors, method="nearest"
    )
    base = Image.open(io.BytesIO(base_png)).convert("RGBA")

    frames = []
    for i in range(frame_count):
        t = i / frame_count
        phase = math.sin(2 * math.pi * t)

        if effect == "bob":
            offset = round(phase * intensity)
            frame = _bob_frame(base, offset)

        elif effect == "shimmer":
            r, g, b, a = base.split()
            rgb = Image.merge("RGB", (r, g, b))
            rgb = _shimmer_frame(rgb.copy(), seed=i, strength=max(1, intensity) * 10)
            r2, g2, b2 = rgb.split()
            frame = Image.merge("RGBA", (r2, g2, b2, a))

        else:
            r, g, b, a = base.split()
            rgb = Image.merge("RGB", (r, g, b))
            factor = 1.0 + phase * (0.15 * max(1, intensity) / 3)
            rgb = _glow_frame(rgb, factor)
            r2, g2, b2 = rgb.split()
            frame = Image.merge("RGBA", (r2, g2, b2, a))

        p_frame = frame.convert("RGBA")
        alpha = p_frame.split()[3]
        p_frame = p_frame.convert("RGB").convert(
            "P", palette=Image.ADAPTIVE, colors=min(255, max(2, palette_colors or 64))
        )
        mask = Image.eval(alpha, lambda a: 255 if a > 0 else 0)
        p_frame.paste(255, mask=Image.eval(mask, lambda a: 255 - a))
        frames.append(p_frame)

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration_ms,
        loop=0,
        disposal=2,
        transparency=255,
    )
    return buf.getvalue()
