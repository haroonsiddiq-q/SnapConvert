from functools import lru_cache
from rembg import remove, new_session
from PIL import Image
import io

AVAILABLE_MODELS = [
    "u2net",
    "u2net_human_seg",
    "isnet-general-use",
    "birefnet-general",
    "birefnet-portrait",
]

@lru_cache(maxsize=None)
def _get_session(model: str):
    return new_session(model)

def remove_background(
    image_bytes: bytes,
    model: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
) -> bytes:
    session = _get_session(model)
    img = Image.open(io.BytesIO(image_bytes))
    result = remove(
        img,
        session=session,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
        alpha_matting_background_threshold=alpha_matting_background_threshold,
        alpha_matting_erode_size=alpha_matting_erode_size,
    )
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
