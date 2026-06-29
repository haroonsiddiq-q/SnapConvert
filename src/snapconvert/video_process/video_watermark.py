import subprocess
import tempfile
import os
from pathlib import Path

POSITIONS = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
MARGIN = 20

# Default font paths per OS — FFmpeg drawtext needs an absolute font path
DEFAULT_FONTS = [
    "C:/Windows/Fonts/arial.ttf",       # Windows
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
    "/System/Library/Fonts/Helvetica.ttc",               # macOS
]


def _find_font(font_path: str = None) -> str:
    """Return the first available font path."""
    candidates = [font_path] + DEFAULT_FONTS if font_path else DEFAULT_FONTS
    for path in candidates:
        if path and os.path.exists(path):
            # FFmpeg on Windows needs forward slashes
            return path.replace("\\", "/")
    raise RuntimeError(
        "No font file found. Install Arial or pass an explicit font_path."
    )


def _ffmpeg_position(position: str, item_w: str, item_h: str) -> tuple:
    """Return (x_expr, y_expr) FFmpeg filter expressions for a named position."""
    m = MARGIN
    positions = {
        "top-left":     (f"{m}",                    f"{m}"),
        "top-right":    (f"W-{item_w}-{m}",         f"{m}"),
        "bottom-left":  (f"{m}",                    f"H-{item_h}-{m}"),
        "bottom-right": (f"W-{item_w}-{m}",         f"H-{item_h}-{m}"),
        "center":       (f"(W-{item_w})/2",         f"(H-{item_h})/2"),
    }
    if position not in positions:
        raise ValueError(f"Invalid position '{position}'. Choose from: {', '.join(POSITIONS)}")
    return positions[position]


def watermark_text_video(
    video_bytes: bytes,
    input_ext: str,
    text: str,
    position: str = "bottom-right",
    font_size: int = 36,
    color: str = "white",
    opacity: float = 0.7,
    font_path: str = None,
) -> bytes:
    """
    Overlay text onto a video using FFmpeg drawtext filter.

    color:    Color name or hex e.g. 'white', '#ffffff'.
    opacity:  0.0–1.0.
    font_path: Absolute path to a .ttf font. Auto-detected if not provided.
    """
    if not text.strip():
        raise ValueError("Text cannot be empty")
    if position not in POSITIONS:
        raise ValueError(f"Invalid position '{position}'. Choose from: {', '.join(POSITIONS)}")
    if not 0.0 <= opacity <= 1.0:
        raise ValueError("Opacity must be between 0.0 and 1.0")

    font = _find_font(font_path)
    alpha = int(opacity * 255)
    # FFmpeg color with alpha: color@alpha_hex
    ffmpeg_color = f"{color}@{alpha/255:.2f}"

    x_expr, y_expr = _ffmpeg_position(position, "tw", "th")

    drawtext = (
        f"drawtext=fontfile='{font}'"
        f":text='{text}'"
        f":fontsize={font_size}"
        f":fontcolor={ffmpeg_color}"
        f":x={x_expr}:y={y_expr}"
    )

    with tempfile.TemporaryDirectory() as tmp:
        input_path  = os.path.join(tmp, f"input.{input_ext}")
        output_path = os.path.join(tmp, f"output.{input_ext}")

        Path(input_path).write_bytes(video_bytes)

        subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", drawtext,
                "-codec:a", "copy",
                output_path,
            ],
            capture_output=True,
            check=True,
        )
        return Path(output_path).read_bytes()


def watermark_image_video(
    video_bytes: bytes,
    input_ext: str,
    watermark_bytes: bytes,
    position: str = "bottom-right",
    scale: int = 20,
    opacity: float = 0.7,
) -> bytes:
    """
    Overlay an image (logo) onto a video using FFmpeg overlay filter.

    scale:   Watermark width as % of video width (1–100).
    opacity: 0.0–1.0.
    """
    if position not in POSITIONS:
        raise ValueError(f"Invalid position '{position}'. Choose from: {', '.join(POSITIONS)}")
    if not 1 <= scale <= 100:
        raise ValueError("Scale must be between 1 and 100")
    if not 0.0 <= opacity <= 1.0:
        raise ValueError("Opacity must be between 0.0 and 1.0")

    x_expr, y_expr = _ffmpeg_position(position, "overlay_w", "overlay_h")

    # Scale watermark to % of video width, then apply opacity
    scale_filter  = f"scale=iw*{scale}/100:-1"
    format_filter = "format=rgba"
    alpha_filter  = f"colorchannelmixer=aa={opacity:.2f}"
    wm_filter     = f"[1:v]{scale_filter},{format_filter},{alpha_filter}[wm]"
    overlay       = f"[0:v][wm]overlay={x_expr}:{y_expr}"
    full_filter   = f"{wm_filter};{overlay}"

    with tempfile.TemporaryDirectory() as tmp:
        input_path  = os.path.join(tmp, f"input.{input_ext}")
        wm_path     = os.path.join(tmp, "watermark.png")
        output_path = os.path.join(tmp, f"output.{input_ext}")

        Path(input_path).write_bytes(video_bytes)
        Path(wm_path).write_bytes(watermark_bytes)

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-i", wm_path,
                "-filter_complex", full_filter,
                "-codec:a", "copy",
                output_path,
            ],
            capture_output=True,
            check=True,
        )
        return Path(output_path).read_bytes()
