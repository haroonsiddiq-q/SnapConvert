import subprocess
import os
from pathlib import Path
from snapconvert.remove_bg.image.image_background_removal import remove_background


def get_video_fps(input_path: str) -> float:
    """Read FPS from video using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    num, den = result.stdout.strip().split("/")
    return float(num) / float(den)


def extract_frames(input_path: str, frames_dir: str) -> None:
    """Extract all video frames as PNGs."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", input_path,
            os.path.join(frames_dir, "frame_%06d.png"),
        ],
        capture_output=True,
        check=True,
    )


def process_frames(
    frames_dir: str,
    output_dir: str,
    model: str,
    alpha_matting: bool,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
) -> None:
    """Run background removal on every extracted frame."""
    for frame_path in sorted(Path(frames_dir).glob("frame_*.png")):
        image_bytes = frame_path.read_bytes()
        result_bytes = remove_background(
            image_bytes,
            model=model,
            alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            alpha_matting_erode_size=alpha_matting_erode_size,
        )
        (Path(output_dir) / frame_path.name).write_bytes(result_bytes)


def assemble_transparent(frames_dir: str, fps: float, output_path: str) -> None:
    """Reassemble RGBA frames into a WEBM with alpha (VP9)."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(frames_dir, "frame_%06d.png"),
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            "-auto-alt-ref", "0",
            "-b:v", "0", "-crf", "30",
            output_path,
        ],
        capture_output=True,
        check=True,
    )


def assemble_rgb(frames_dir: str, fps: float, output_path: str) -> None:
    """Reassemble RGB frames into an MP4 (H.264)."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(frames_dir, "frame_%06d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "23",
            output_path,
        ],
        capture_output=True,
        check=True,
    )
