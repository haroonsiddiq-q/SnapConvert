from PIL import Image
import io

UPSCALE_METHODS = ["lanczos", "realesrgan"]
UPSCALE_FACTORS = [2, 4]


def _upscale_lanczos(img: Image.Image, scale: int) -> Image.Image:
    """Fast high-quality upscale using Pillow Lanczos resampling."""
    new_w = img.width  * scale
    new_h = img.height * scale
    return img.resize((new_w, new_h), Image.LANCZOS)


def _upscale_realesrgan(img: Image.Image, scale: int) -> Image.Image:
    """
    AI upscale using Real-ESRGAN.
    Model auto-downloads to ~/.cache on first use (~60MB for 2x, ~65MB for 4x).
    Requires: pip install realesrgan
    """
    try:
        import torch
        from realesrgan import RealESRGANer
        from basicsr.archs.rrdbnet_arch import RRDBNet
    except ImportError:
        raise RuntimeError(
            "Real-ESRGAN is not installed. "
            "Run: uv add realesrgan "
            "or use method='lanczos' instead."
        )

    import numpy as np

    model_urls = {
        2: "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        4: "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    }

    # RRDBNet config differs between 2x and 4x models
    if scale == 2:
        arch = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
    else:
        arch = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    upsampler = RealESRGANer(
        scale=scale,
        model_path=model_urls[scale],
        model=arch,
        tile=0,
        tile_pad=10,
        pre_pad=0,
        half=False,
        device=device,
    )

    # Real-ESRGAN expects BGR numpy array
    img_rgb = img.convert("RGB")
    img_bgr = np.array(img_rgb)[:, :, ::-1]
    output_bgr, _ = upsampler.enhance(img_bgr, outscale=scale)

    # Convert back to RGB PIL
    output_rgb = output_bgr[:, :, ::-1]
    return Image.fromarray(output_rgb)


def upscale_image(
    image_bytes: bytes,
    scale: int = 2,
    method: str = "lanczos",
) -> bytes:
    """
    Upscale an image by 2x or 4x.

    scale:  2 or 4.
    method: 'lanczos'    — fast, no extra dependencies, good quality.
            'realesrgan' — AI super resolution, best quality, requires
                           realesrgan package and ~60MB model download on first use.

    Preserves transparency (RGBA) for lanczos.
    Real-ESRGAN outputs RGB only (transparency flattened to white).
    Returns PNG bytes.
    """
    if scale not in UPSCALE_FACTORS:
        raise ValueError(f"Invalid scale '{scale}'. Choose from: {', '.join(map(str, UPSCALE_FACTORS))}")
    if method not in UPSCALE_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose from: {', '.join(UPSCALE_METHODS)}")

    img = Image.open(io.BytesIO(image_bytes))

    if method == "lanczos":
        img = img.convert("RGBA")
        result = _upscale_lanczos(img, scale)
    else:
        # Real-ESRGAN doesn't support alpha — flatten to white first
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
            img = background
        else:
            img = img.convert("RGB")
        result = _upscale_realesrgan(img, scale)

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()
