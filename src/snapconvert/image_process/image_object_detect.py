from ultralytics import YOLO
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
import io

MODEL_SIZES = ["n", "s", "m"]

# Distinct colors per class index (cycles if more than 20 classes)
COLORS = [
    (255, 56,  56),  (255, 157, 151), (255, 112, 31),  (255, 178, 29),
    (207, 210,  49), (72,  249, 10),  (146, 204, 23),  (61,  219, 134),
    (26,  147, 52),  (0,   212, 187), (44,  153, 168), (0,   194, 255),
    (52,  69,  147), (100, 115, 255), (0,   24,  236), (132, 56,  255),
    (82,  0,   133), (203, 56,  255), (255, 149, 200), (255, 55,  199),
]


@lru_cache(maxsize=None)
def _get_model(model_size: str) -> YOLO:
    return YOLO(f"yolov8{model_size}.pt")


def _get_color(class_id: int) -> tuple:
    return COLORS[class_id % len(COLORS)]


def _draw_detections(img: Image.Image, boxes, show_labels: bool, show_confidence: bool) -> list:
    """Draw bounding boxes on image. Returns list of detection dicts."""
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except (IOError, OSError):
        font = ImageFont.load_default()

    detections = []
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        class_id   = int(box.cls[0])
        label      = boxes.names[class_id]
        confidence = float(box.conf[0])
        color      = _get_color(class_id)

        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        if show_labels or show_confidence:
            parts = []
            if show_labels:
                parts.append(label)
            if show_confidence:
                parts.append(f"{confidence:.0%}")
            text  = " ".join(parts)
            bbox  = draw.textbbox((x1, y1), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.rectangle([x1, y1 - text_h - 6, x1 + text_w + 6, y1], fill=color)
            draw.text((x1 + 3, y1 - text_h - 3), text, fill=(255, 255, 255), font=font)

        detections.append({
            "label":      label,
            "confidence": round(confidence, 3),
            "box":        {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        })

    return detections


def detect_objects(
    image_bytes: bytes,
    model_size: str = "n",
    confidence: float = 0.5,
    show_labels: bool = True,
    show_confidence: bool = True,
) -> tuple:
    """
    Run YOLOv8 object detection on an image.

    model_size: 'n' (nano, fastest), 's' (small), 'm' (medium).
    confidence: Minimum detection confidence 0.0–1.0.
    show_labels:     Draw class name on each box.
    show_confidence: Draw confidence % on each box.

    Returns (annotated_image_bytes, detections_list).
    """
    if model_size not in MODEL_SIZES:
        raise ValueError(f"Invalid model_size '{model_size}'. Choose from: {', '.join(MODEL_SIZES)}")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    model  = _get_model(model_size)
    img    = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    result = model(img, conf=confidence, verbose=False)[0]

    annotated  = img.copy()
    detections = _draw_detections(annotated, result.boxes, show_labels, show_confidence)

    buf = io.BytesIO()
    annotated.save(buf, format="PNG")
    return buf.getvalue(), detections


def detect_objects_frame(
    image_bytes: bytes,
    model: YOLO,
    confidence: float,
    show_labels: bool,
    show_confidence: bool,
) -> bytes:
    """Process a single frame — used by video detection."""
    img    = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    result = model(img, conf=confidence, verbose=False)[0]
    annotated = img.copy()
    _draw_detections(annotated, result.boxes, show_labels, show_confidence)
    buf = io.BytesIO()
    annotated.save(buf, format="PNG")
    return buf.getvalue()
