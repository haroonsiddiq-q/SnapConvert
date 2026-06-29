from PIL import Image
import io
from typing import List

# Page sizes in points (1 point = 1/72 inch)
PAGE_SIZES = {
    "a4":     (595, 842),
    "letter": (612, 792),
}

FIT_MODES = ["fit", "fill", "original"]


def _to_rgb(img: Image.Image) -> Image.Image:
    """Flatten transparency onto white — PDF doesn't support alpha."""
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
        return background
    return img.convert("RGB")


def _scale_to_fit(img: Image.Image, page_w: int, page_h: int) -> Image.Image:
    """Scale image to fit within page, preserving aspect ratio."""
    img_w, img_h = img.size
    scale = min(page_w / img_w, page_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    return img.resize((new_w, new_h), Image.LANCZOS)


def _scale_to_fill(img: Image.Image, page_w: int, page_h: int) -> Image.Image:
    """Scale image to fill page, preserving aspect ratio (may crop)."""
    img_w, img_h = img.size
    scale = max(page_w / img_w, page_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    # Center crop to page size
    left = (new_w - page_w) // 2
    top  = (new_h - page_h) // 2
    return resized.crop((left, top, left + page_w, top + page_h))


def _place_on_page(img: Image.Image, page_w: int, page_h: int) -> Image.Image:
    """Center image on a white page canvas."""
    page = Image.new("RGB", (page_w, page_h), (255, 255, 255))
    x = (page_w - img.width)  // 2
    y = (page_h - img.height) // 2
    page.paste(img, (x, y))
    return page


def images_to_pdf(
    images_bytes_list: List[bytes],
    page_size: str = "a4",
    fit: str = "fit",
) -> bytes:
    """
    Combine one or more images into a single PDF.

    page_size: 'a4', 'letter', or 'auto' (page matches each image's dimensions).
    fit:       'fit'      — scale to fit page, preserve ratio, no cropping.
               'fill'     — scale to fill page, preserve ratio, may crop edges.
               'original' — no scaling, image centered on page.

    Returns PDF bytes.
    """
    page_size = page_size.lower()
    fit = fit.lower()

    if page_size not in (*PAGE_SIZES, "auto"):
        raise ValueError(f"Invalid page_size '{page_size}'. Choose from: a4, letter, auto")
    if fit not in FIT_MODES:
        raise ValueError(f"Invalid fit '{fit}'. Choose from: {', '.join(FIT_MODES)}")
    if not images_bytes_list:
        raise ValueError("At least one image is required")

    pages = []

    for image_bytes in images_bytes_list:
        img = _to_rgb(Image.open(io.BytesIO(image_bytes)))

        if page_size == "auto":
            page_w, page_h = img.size
        else:
            page_w, page_h = PAGE_SIZES[page_size]

        if fit == "fit":
            img = _scale_to_fit(img, page_w, page_h)
            img = _place_on_page(img, page_w, page_h)
        elif fit == "fill":
            img = _scale_to_fill(img, page_w, page_h)
        else:  # original
            img = _place_on_page(img, page_w, page_h)

        pages.append(img)

    buf = io.BytesIO()
    pages[0].save(
        buf,
        format="PDF",
        save_all=True,
        append_images=pages[1:],
        resolution=72,
    )
    return buf.getvalue()
