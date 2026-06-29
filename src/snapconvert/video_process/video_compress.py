import subprocess
import tempfile
import os
from pathlib import Path

PRESETS = ["ultrafast", "fast", "medium", "slow"]

# Formats that support libx264 (H.264)
H264_FORMATS = {"mp4", "mov"}
# Formats that use VP9
VP9_FORMATS  = {"webm"}


def compress_video(
    video_bytes: bytes,
    input_ext: str,
    crf: int = 28,
    preset: str = "medium",
) -> bytes:
    """
    Re-encode a video with higher compression, keeping the same format.

    crf:    Constant Rate Factor — controls quality vs size tradeoff.
            H.264 (mp4/mov): 0–51, default 28. Higher = smaller file, lower quality.
            VP9   (webm):    0–63, default 28. Same direction.
    preset: Encoding speed — 'ultrafast', 'fast', 'medium', 'slow'.
            Slower preset = better compression at the same CRF.
            Only applies to H.264 (mp4/mov); ignored for VP9 and AVI.

    Returns compressed video bytes in the same format as input.
    """
    ext = input_ext.lower()

    if preset not in PRESETS:
        raise ValueError(f"Invalid preset '{preset}'. Choose from: {', '.join(PRESETS)}")
    if crf < 0 or crf > 63:
        raise ValueError("CRF must be between 0 and 63")

    with tempfile.TemporaryDirectory() as tmp:
        input_path  = os.path.join(tmp, f"input.{ext}")
        output_path = os.path.join(tmp, f"output.{ext}")

        Path(input_path).write_bytes(video_bytes)

        if ext in H264_FORMATS:
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-c:v", "libx264",
                "-crf", str(crf),
                "-preset", preset,
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                output_path,
            ]
        elif ext in VP9_FORMATS:
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-c:v", "libvpx-vp9",
                "-crf", str(crf),
                "-b:v", "0",
                "-c:a", "copy",
                output_path,
            ]
        else:
            # Fallback — let FFmpeg pick the codec for the container
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-crf", str(crf),
                "-c:a", "copy",
                output_path,
            ]

        subprocess.run(cmd, capture_output=True, check=True)
        return Path(output_path).read_bytes()
