import tempfile
import os
import io
from pathlib import Path
from PIL import Image, ImageOps
from snapconvert.remove_bg.video._utils import (
    get_video_fps,
    extract_frames,
    process_frames,
    assemble_rgb,
)


def _apply_image_bg_to_frames(frames_dir: str, output_dir: str, background_bytes: bytes) -> None:
    bg_source = Image.open(io.BytesIO(background_bytes)).convert("RGBA")

    for frame_path in sorted(Path(frames_dir).glob("frame_*.png")):
        fg = Image.open(frame_path).convert("RGBA")
        bg = ImageOps.fit(bg_source.copy(), fg.size)
        bg.paste(fg, mask=fg.split()[3])
        buf = io.BytesIO()
        bg.convert("RGB").save(buf, format="PNG")
        (Path(output_dir) / frame_path.name).write_bytes(buf.getvalue())


def replace_background(
    video_bytes: bytes,
    background_bytes: bytes,
    model: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
) -> bytes:
    """Remove background from video → composite onto a static background image → MP4."""
    with tempfile.TemporaryDirectory() as tmp:
        input_path   = os.path.join(tmp, "input.mp4")
        frames_dir   = os.path.join(tmp, "frames");   os.makedirs(frames_dir)
        removed_dir  = os.path.join(tmp, "removed");  os.makedirs(removed_dir)
        replaced_dir = os.path.join(tmp, "replaced"); os.makedirs(replaced_dir)
        output_path  = os.path.join(tmp, "output.mp4")

        Path(input_path).write_bytes(video_bytes)
        fps = get_video_fps(input_path)
        extract_frames(input_path, frames_dir)
        process_frames(
            frames_dir, removed_dir, model, alpha_matting,
            alpha_matting_foreground_threshold,
            alpha_matting_background_threshold,
            alpha_matting_erode_size,
        )
        _apply_image_bg_to_frames(removed_dir, replaced_dir, background_bytes)
        assemble_rgb(replaced_dir, fps, output_path)
        return Path(output_path).read_bytes()
