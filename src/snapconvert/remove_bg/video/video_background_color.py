import tempfile
import os
import re
import io
from pathlib import Path
from PIL import Image
from snapconvert.remove_bg.video._utils import (
    get_video_fps,
    extract_frames,
    process_frames,
    assemble_rgb,
)


def _apply_color_to_frames(frames_dir: str, output_dir: str, hex_color: str) -> None:
    hex_color = hex_color.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", hex_color):
        raise ValueError(f"Invalid hex color: #{hex_color}")
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    for frame_path in sorted(Path(frames_dir).glob("frame_*.png")):
        fg = Image.open(frame_path).convert("RGBA")
        bg = Image.new("RGBA", fg.size, (r, g, b, 255))
        bg.paste(fg, mask=fg.split()[3])
        buf = io.BytesIO()
        bg.convert("RGB").save(buf, format="PNG")
        (Path(output_dir) / frame_path.name).write_bytes(buf.getvalue())


def apply_background_color(
    video_bytes: bytes,
    hex_color: str = "#ffffff",
    model: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
) -> bytes:
    """Remove background from video → solid colour MP4."""
    with tempfile.TemporaryDirectory() as tmp:
        input_path  = os.path.join(tmp, "input.mp4")
        frames_dir  = os.path.join(tmp, "frames");  os.makedirs(frames_dir)
        removed_dir = os.path.join(tmp, "removed"); os.makedirs(removed_dir)
        color_dir   = os.path.join(tmp, "color");   os.makedirs(color_dir)
        output_path = os.path.join(tmp, "output.mp4")

        Path(input_path).write_bytes(video_bytes)
        fps = get_video_fps(input_path)
        extract_frames(input_path, frames_dir)
        process_frames(
            frames_dir, removed_dir, model, alpha_matting,
            alpha_matting_foreground_threshold,
            alpha_matting_background_threshold,
            alpha_matting_erode_size,
        )
        _apply_color_to_frames(removed_dir, color_dir, hex_color)
        assemble_rgb(color_dir, fps, output_path)
        return Path(output_path).read_bytes()
