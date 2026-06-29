import subprocess
import tempfile
import os
import io
import zipfile
from pathlib import Path
from typing import Optional


def extract_frames(
    video_bytes: bytes,
    input_ext: str,
    fps: Optional[float] = None,
    quality: int = 3,
) -> bytes:
    """
    Extract frames from a video and return them as a ZIP of PNGs.

    fps:     Frames per second to extract.
             None  = every frame (original fps).
             1     = 1 frame per second.
             0.5   = 1 frame every 2 seconds.
    quality: PNG compression level 1–9.
             Lower = larger file, faster to write.
             Higher = smaller file, slower to write.
             Default 3 is a good balance.

    Returns ZIP bytes containing frame_000001.png, frame_000002.png, ...
    """
    if quality < 1 or quality > 9:
        raise ValueError("Quality must be between 1 and 9")
    if fps is not None and fps <= 0:
        raise ValueError("fps must be greater than 0")

    with tempfile.TemporaryDirectory() as tmp:
        input_path = os.path.join(tmp, f"input.{input_ext}")
        frames_dir = os.path.join(tmp, "frames")
        os.makedirs(frames_dir)

        Path(input_path).write_bytes(video_bytes)

        # Build vf filter — only add fps filter if specified
        vf_parts = []
        if fps is not None:
            vf_parts.append(f"fps={fps}")

        ffmpeg_cmd = ["ffmpeg", "-y", "-i", input_path]
        if vf_parts:
            ffmpeg_cmd += ["-vf", ",".join(vf_parts)]
        ffmpeg_cmd += [
            "-compression_level", str(quality),
            os.path.join(frames_dir, "frame_%06d.png"),
        ]

        subprocess.run(ffmpeg_cmd, capture_output=True, check=True)

        # Pack all frames into a ZIP in memory
        frame_paths = sorted(Path(frames_dir).glob("frame_*.png"))
        if not frame_paths:
            raise RuntimeError("No frames were extracted — check that the video file is valid")

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_STORED) as zf:
            for frame_path in frame_paths:
                zf.writestr(frame_path.name, frame_path.read_bytes())

        return zip_buf.getvalue()
