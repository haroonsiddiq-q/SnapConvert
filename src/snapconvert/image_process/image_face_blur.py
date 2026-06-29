import cv2
import numpy as np
from PIL import Image
import io

BLUR_STYLES = ["gaussian", "pixelate", "mosaic"]


def _to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _ensure_odd(value: int) -> int:
    """Blur kernel must be odd — round up if even."""
    return value if value % 2 == 1 else value + 1


def _apply_gaussian(region: np.ndarray, strength: int) -> np.ndarray:
    """Smooth Gaussian blur."""
    strength = _ensure_odd(strength)
    return cv2.GaussianBlur(region, (strength, strength), 0)


def _apply_pixelate(region: np.ndarray, strength: int) -> np.ndarray:
    """
    Pixelate by downscaling then upscaling.
    strength controls block size — higher = bigger pixels.
    Clamped so the region is never shrunk below 1px.
    """
    h, w = region.shape[:2]
    # Map strength (1–99) to a pixel block size (2–max dimension/2)
    block = max(2, int(strength / 10) + 2)
    small_w = max(1, w // block)
    small_h = max(1, h // block)
    small   = cv2.resize(region, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def _apply_mosaic(region: np.ndarray, strength: int) -> np.ndarray:
    """
    Large visible square blocks — like the classic face censor effect.
    Maps strength 1–99 to block size 2–33px for clearly visible squares.
    """
    h, w = region.shape[:2]
    block   = max(2, int(strength / 3))
    small_w = max(1, w // block)
    small_h = max(1, h // block)
    small   = cv2.resize(region, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def blur_faces(
    image_bytes: bytes,
    blur_strength: int = 51,
    min_face_size: int = 30,
    style: str = "gaussian",
) -> tuple:
    """
    Detect faces and apply blur or pixelate effect to each one.

    blur_strength: Intensity 1–99. Higher = stronger effect.
    min_face_size: Minimum face width/height in pixels to detect.
    style:         'gaussian' — smooth blur. 'pixelate' — subtle pixel blocks. 'mosaic' — large visible square blocks.

    Returns (processed_image_bytes, face_count).
    """
    if not 1 <= blur_strength <= 99:
        raise ValueError("blur_strength must be between 1 and 99")
    if min_face_size < 1:
        raise ValueError("min_face_size must be at least 1")
    if style not in BLUR_STYLES:
        raise ValueError(f"Invalid style '{style}'. Choose from: {', '.join(BLUR_STYLES)}")

    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    # OpenCV works in BGR — convert RGB channels only for detection
    rgb  = np.array(pil_img.convert("RGB"))
    bgr  = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector     = cv2.CascadeClassifier(cascade_path)

    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(min_face_size, min_face_size),
    )

    face_count = len(faces) if len(faces) > 0 else 0
    if face_count == 0:
        return _to_png(pil_img), 0

    img_array = np.array(pil_img)  # RGBA
    for (x, y, w, h) in faces:
        region = img_array[y:y+h, x:x+w, :3]  # RGB only
        if style == "gaussian":
            img_array[y:y+h, x:x+w, :3] = _apply_gaussian(region, blur_strength)
        elif style == "pixelate":
            img_array[y:y+h, x:x+w, :3] = _apply_pixelate(region, blur_strength)
        else:
            img_array[y:y+h, x:x+w, :3] = _apply_mosaic(region, blur_strength)

    result = Image.fromarray(img_array, "RGBA")
    return _to_png(result), face_count
