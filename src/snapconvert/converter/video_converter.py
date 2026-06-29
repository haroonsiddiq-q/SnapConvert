import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional

# Maps output_format to (file_extension, ffmpeg_args)
FORMAT_CONFIG = {
    "mp4":  ("mp4",  ["-c:v", "libx264", "-pix_fmt", "yuv420p"]),
    "webm": ("webm", ["-c:v", "libvpx-vp9", "-b:v", "0"]),
    "mov":  ("mov",  ["-c:v", "libx264", "-pix_fmt", "yuv420p"]),
    "gif":  ("gif",  []),  # GIF handled separately with palette pass
}

# Default CRF per format (lower = better quality, larger file)
DEFAULT_CRF = {
    "mp4":  23,
    "webm": 31,
    "mov":  23,
    "gif":  None,  # GIF uses dithering, not CRF
}


def _build_trim_args(start_time: Optional[str], end_time: Optional[str]) -> list:
    """Build FFmpeg -ss / -to trim arguments."""
    args = []
    if start_time:
        args += ["-ss", start_time]
    if end_time:
        args += ["-to", end_time]
    return args


def _convert_to_gif(input_path: str, output_path: str, trim_args: list[str]):
    """2-pass palette-optimized GIF conversion."""
    palette_path = output_path + "_palette.png"
    try:
        # Pass 1 — generate palette
        subprocess.run(
            ["ffmpeg", "-y"] + trim_args + [
                "-i", input_path,
                "-vf", "fps=15,scale=480:-1:flags=lanczos,palettegen",
                palette_path,
            ],
            capture_output=True,
            check=True,
        )
        # Pass 2 — render GIF using palette
        subprocess.run(
            ["ffmpeg", "-y"] + trim_args + [
                "-i", input_path,
                "-i", palette_path,
                "-lavfi", "fps=15,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse",
                output_path,
            ],
            capture_output=True,
            check=True,
        )
    finally:
        if os.path.exists(palette_path):
            os.remove(palette_path)


def convert_video(
    video_bytes: bytes,
    input_ext: str,
    output_format: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    crf: Optional[int] = None,
) -> tuple:
    """
    Convert, trim, and/or compress a video.

    start_time / end_time accept "ss", "mm:ss", or "hh:mm:ss".
    crf controls quality (lower = better). Ignored for GIF.

    Returns (video_bytes, output_extension).
    """
    fmt = output_format.lower()
    if fmt not in FORMAT_CONFIG:
        raise ValueError(f"Unsupported format: {output_format}. Choose from: {', '.join(FORMAT_CONFIG)}")

    ext, codec_args = FORMAT_CONFIG[fmt]
    effective_crf = crf if crf is not None else DEFAULT_CRF[fmt]
    trim_args = _build_trim_args(start_time, end_time)

    with tempfile.TemporaryDirectory() as tmp:
        input_path  = os.path.join(tmp, f"input.{input_ext}")
        output_path = os.path.join(tmp, f"output.{ext}")

        Path(input_path).write_bytes(video_bytes)

        if fmt == "gif":
            _convert_to_gif(input_path, output_path, trim_args)
        else:
            crf_args = ["-crf", str(effective_crf)] if effective_crf is not None else []
            subprocess.run(
                ["ffmpeg", "-y"] + trim_args + [
                    "-i", input_path,
                ] + codec_args + crf_args + [
                    output_path,
                ],
                capture_output=True,
                check=True,
            )

        return Path(output_path).read_bytes(), ext
