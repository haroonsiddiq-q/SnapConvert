import os
import tempfile
from pathlib import Path
from snapconvert.image_process.image_object_detect import _get_model, detect_objects_frame
from snapconvert.remove_bg.video._utils import get_video_fps, extract_frames, assemble_rgb


def detect_objects_video(
    video_bytes: bytes,
    input_ext: str,
    model_size: str = "n",
    confidence: float = 0.5,
    show_labels: bool = True,
    show_confidence: bool = True,
) -> bytes:
    """
    Run YOLOv8 object detection on every frame of a video.

    model_size: 'n' (nano, fastest), 's' (small), 'm' (medium).
    confidence: Minimum detection confidence 0.0–1.0.

    Returns annotated MP4 bytes.
    """
    with tempfile.TemporaryDirectory() as tmp:
        input_path   = os.path.join(tmp, f"input.{input_ext}")
        frames_dir   = os.path.join(tmp, "frames");   os.makedirs(frames_dir)
        detected_dir = os.path.join(tmp, "detected"); os.makedirs(detected_dir)
        output_path  = os.path.join(tmp, "output.mp4")

        Path(input_path).write_bytes(video_bytes)
        fps = get_video_fps(input_path)
        extract_frames(input_path, frames_dir)

        model = _get_model(model_size)

        for frame_path in sorted(Path(frames_dir).glob("frame_*.png")):
            result = detect_objects_frame(
                frame_path.read_bytes(),
                model=model,
                confidence=confidence,
                show_labels=show_labels,
                show_confidence=show_confidence,
            )
            (Path(detected_dir) / frame_path.name).write_bytes(result)

        assemble_rgb(detected_dir, fps, output_path)
        return Path(output_path).read_bytes()
