import tempfile
import os
from pathlib import Path
from snapconvert.remove_bg.video._utils import (
    get_video_fps,
    extract_frames,
    process_frames,
    assemble_transparent,
)


def remove_background(
    video_bytes: bytes,
    model: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
) -> bytes:
    """Remove background from video → transparent WEBM (VP9 + alpha)."""
    with tempfile.TemporaryDirectory() as tmp:
        input_path  = os.path.join(tmp, "input.mp4")
        frames_dir  = os.path.join(tmp, "frames");  os.makedirs(frames_dir)
        removed_dir = os.path.join(tmp, "removed"); os.makedirs(removed_dir)
        output_path = os.path.join(tmp, "output.webm")

        Path(input_path).write_bytes(video_bytes)
        fps = get_video_fps(input_path)
        extract_frames(input_path, frames_dir)
        process_frames(
            frames_dir, removed_dir, model, alpha_matting,
            alpha_matting_foreground_threshold,
            alpha_matting_background_threshold,
            alpha_matting_erode_size,
        )
        assemble_transparent(removed_dir, fps, output_path)
        return Path(output_path).read_bytes()
