from fastapi import FastAPI, UploadFile, HTTPException, Query
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Optional, List, List
from snapconvert.remove_bg.image.image_background_removal import remove_background, AVAILABLE_MODELS
from snapconvert.remove_bg.image.image_background_color import apply_background_color
from snapconvert.remove_bg.image.image_background_replace import replace_background
from snapconvert.remove_bg.video.video_background_removal import remove_background as remove_video_background
from snapconvert.remove_bg.video.video_background_color import apply_background_color as apply_video_background_color
from snapconvert.remove_bg.video.video_background_replace import replace_background as replace_video_background
from snapconvert.converter.image_converter import convert_image, FORMAT_MAP as IMAGE_FORMAT_MAP
from snapconvert.converter.video_converter import convert_video, FORMAT_CONFIG as VIDEO_FORMAT_CONFIG
from snapconvert.image_process.image_crop import crop_manual, crop_smart
from snapconvert.image_process.image_rotate_flip import rotate_image, flip_image, FLIP_DIRECTIONS
from snapconvert.image_process.image_filters import apply_filters
from snapconvert.image_process.image_exif import read_exif, strip_exif
from snapconvert.image_process.image_to_pdf import images_to_pdf, PAGE_SIZES, FIT_MODES
from snapconvert.video_process.video_to_frames import extract_frames as extract_video_frames
from snapconvert.video_process.video_compress import compress_video, PRESETS as VIDEO_PRESETS
from snapconvert.image_process.image_watermark import watermark_text, watermark_image, POSITIONS as WATERMARK_POSITIONS
from snapconvert.image_process.image_face_blur import blur_faces, BLUR_STYLES
from snapconvert.image_process.image_object_detect import detect_objects, MODEL_SIZES as YOLO_MODEL_SIZES
from snapconvert.image_process.image_upscale import upscale_image, UPSCALE_METHODS, UPSCALE_FACTORS
from snapconvert.video_process.video_object_detect import detect_objects_video
from snapconvert.video_process.video_watermark import watermark_text_video, watermark_image_video
import zipfile
import io
import subprocess

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}

app = FastAPI(title="SnapConvert")

# Serve the frontend
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse(_static_dir / "index.html")


@app.post("/image/remove-bg")
async def remove_bg_endpoint(
    file: UploadFile,
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=True),
    alpha_matting_foreground_threshold: int = Query(default=240),
    alpha_matting_background_threshold: int = Query(default=10),
    alpha_matting_erode_size: int = Query(default=10),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    result = remove_background(
        contents, model=model, alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
        alpha_matting_background_threshold=alpha_matting_background_threshold,
        alpha_matting_erode_size=alpha_matting_erode_size,
    )

    out_filename = file.filename.rsplit(".", 1)[0] + ".png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/remove-bg/batch")
async def remove_bg_batch(
    files: list[UploadFile],
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=True),
    alpha_matting_foreground_threshold: int = Query(default=240),
    alpha_matting_background_threshold: int = Query(default=10),
    alpha_matting_erode_size: int = Query(default=10),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is not an image"
                )
            contents = await file.read()
            result = remove_background(
                contents, model=model, alpha_matting=alpha_matting,
                alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                alpha_matting_background_threshold=alpha_matting_background_threshold,
                alpha_matting_erode_size=alpha_matting_erode_size,
            )
            out_filename = file.filename.rsplit(".", 1)[0] + ".png"
            zf.writestr(out_filename, result)

    zip_buf.seek(0)
    return Response(
        content=zip_buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=removed_backgrounds.zip"}
    )


@app.post("/image/color-bg")
async def apply_bg_color_endpoint(
    file: UploadFile,
    color: str = Query(default="#ffffff", description="Hex color e.g. #ff0000"),
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=True),
    alpha_matting_foreground_threshold: int = Query(default=240),
    alpha_matting_background_threshold: int = Query(default=10),
    alpha_matting_erode_size: int = Query(default=10),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    removed = remove_background(
        contents, model=model, alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
        alpha_matting_background_threshold=alpha_matting_background_threshold,
        alpha_matting_erode_size=alpha_matting_erode_size,
    )

    try:
        result = apply_background_color(removed, hex_color=color)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + ".png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/replace-bg")
async def replace_bg_endpoint(
    file: UploadFile,
    background: UploadFile,
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=True),
    alpha_matting_foreground_threshold: int = Query(default=240),
    alpha_matting_background_threshold: int = Query(default=10),
    alpha_matting_erode_size: int = Query(default=10),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Subject file must be an image")
    if not background.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Background file must be an image")

    contents = await file.read()
    bg_contents = await background.read()

    removed = remove_background(
        contents, model=model, alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
        alpha_matting_background_threshold=alpha_matting_background_threshold,
        alpha_matting_erode_size=alpha_matting_erode_size,
    )
    result = replace_background(removed, bg_contents)

    out_filename = file.filename.rsplit(".", 1)[0] + ".png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/video/remove-bg")
async def remove_bg_video_transparent(
    file: UploadFile,
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=False),
    alpha_matting_foreground_threshold: int = Query(default=240),
    alpha_matting_background_threshold: int = Query(default=10),
    alpha_matting_erode_size: int = Query(default=10),
):
    """Remove background from video → transparent WEBM (VP9 + alpha)."""
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")

    contents = await file.read()
    try:
        result = remove_video_background(
            contents, model=model, alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            alpha_matting_erode_size=alpha_matting_erode_size,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    out_filename = file.filename.rsplit(".", 1)[0] + ".webm"
    return Response(
        content=result,
        media_type="video/webm",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/video/color-bg")
async def remove_bg_video_color(
    file: UploadFile,
    color: str = Query(default="#ffffff", description="Hex color e.g. #00ff00"),
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=False),
    alpha_matting_foreground_threshold: int = Query(default=240),
    alpha_matting_background_threshold: int = Query(default=10),
    alpha_matting_erode_size: int = Query(default=10),
):
    """Remove background from video → solid colour MP4."""
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")

    contents = await file.read()
    try:
        result = apply_video_background_color(
            contents, hex_color=color, model=model, alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            alpha_matting_erode_size=alpha_matting_erode_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    out_filename = file.filename.rsplit(".", 1)[0] + "_color_bg.mp4"
    return Response(
        content=result,
        media_type="video/mp4",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/video/replace-bg")
async def remove_bg_video_replace(
    file: UploadFile,
    background: UploadFile,
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=False),
    alpha_matting_foreground_threshold: int = Query(default=240),
    alpha_matting_background_threshold: int = Query(default=10),
    alpha_matting_erode_size: int = Query(default=10),
):
    """Remove background from video → composite onto a static background image → MP4."""
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="Subject file must be a video")
    if not background.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Background file must be an image")

    contents = await file.read()
    bg_contents = await background.read()
    try:
        result = replace_video_background(
            contents, bg_contents, model=model, alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            alpha_matting_erode_size=alpha_matting_erode_size,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    out_filename = file.filename.rsplit(".", 1)[0] + "_replaced_bg.mp4"
    return Response(
        content=result,
        media_type="video/mp4",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/convert")
async def image_convert_endpoint(
    file: UploadFile,
    output_format: str = Query(description=f"Output format. One of: {', '.join(IMAGE_FORMAT_MAP)}"),
    width: Optional[int] = Query(default=None, description="Target width in pixels"),
    height: Optional[int] = Query(default=None, description="Target height in pixels"),
    scale: Optional[float] = Query(default=None, description="Scale by percentage e.g. 50 = 50%"),
    quality: int = Query(default=85, description="Quality 1–95 (applies to JPEG, WEBP, AVIF)"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result, out_ext = convert_image(
            contents,
            output_format=output_format,
            width=width,
            height=height,
            scale=scale,
            quality=quality,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + f".{out_ext}"
    return Response(
        content=result,
        media_type=f"image/{out_ext}",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/video/convert")
async def video_convert_endpoint(
    file: UploadFile,
    output_format: str = Query(description=f"Output format. One of: {', '.join(VIDEO_FORMAT_CONFIG)}"),
    start_time: Optional[str] = Query(default=None, description="Trim start e.g. 0:10 or 00:00:10"),
    end_time: Optional[str] = Query(default=None, description="Trim end e.g. 0:30 or 00:00:30"),
    crf: Optional[int] = Query(default=None, description="Quality 0–51, lower = better (ignored for GIF)"),
):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")

    input_ext = file.filename.rsplit(".", 1)[-1].lower()
    contents = await file.read()
    try:
        result, out_ext = convert_video(
            contents,
            input_ext=input_ext,
            output_format=output_format,
            start_time=start_time,
            end_time=end_time,
            crf=crf,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    media_type = "image/gif" if out_ext == "gif" else f"video/{out_ext}"
    out_filename = file.filename.rsplit(".", 1)[0] + f".{out_ext}"
    return Response(
        content=result,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/crop")
async def image_crop_endpoint(
    file: UploadFile,
    x: int = Query(description="Left edge of crop box in pixels"),
    y: int = Query(description="Top edge of crop box in pixels"),
    width: int = Query(description="Width of crop box in pixels"),
    height: int = Query(description="Height of crop box in pixels"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result = crop_manual(contents, x=x, y=y, width=width, height=height)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_cropped.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/crop/smart")
async def image_crop_smart_endpoint(
    file: UploadFile,
    padding: int = Query(default=10, description="Padding in pixels around the subject"),
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result = crop_smart(contents, padding=padding, model=model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_smartcrop.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/rotate")
async def image_rotate_endpoint(
    file: UploadFile,
    degrees: float = Query(description="Degrees to rotate counter-clockwise"),
    expand: bool = Query(default=True, description="Expand canvas to fit rotated image"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    result = rotate_image(contents, degrees=degrees, expand=expand)

    out_filename = file.filename.rsplit(".", 1)[0] + "_rotated.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/flip")
async def image_flip_endpoint(
    file: UploadFile,
    direction: str = Query(description=f"Flip direction. One of: {', '.join(FLIP_DIRECTIONS)}"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result = flip_image(contents, direction=direction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_flipped.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/filters")
async def image_filters_endpoint(
    file: UploadFile,
    brightness: float = Query(default=1.0, description="Brightness multiplier (1.0 = original)"),
    contrast: float = Query(default=1.0, description="Contrast multiplier (1.0 = original)"),
    saturation: float = Query(default=1.0, description="Saturation multiplier (1.0 = original)"),
    sharpness: float = Query(default=1.0, description="Sharpness multiplier (1.0 = original)"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result = apply_filters(
            contents,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            sharpness=sharpness,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_filtered.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/read-exif")
async def image_read_exif_endpoint(file: UploadFile):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    tags = read_exif(contents)
    return {"filename": file.filename, "exif": tags, "count": len(tags)}


@app.post("/image/strip-exif")
async def image_strip_exif_endpoint(
    file: UploadFile,
    output_format: str = Query(default="jpeg", description="Output format: jpeg, png, webp"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result, out_ext = strip_exif(contents, output_format=output_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + f"_clean.{out_ext}"
    return Response(
        content=result,
        media_type=f"image/{out_ext}",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/to-pdf")
async def image_to_pdf_endpoint(
    files: List[UploadFile],
    page_size: str = Query(default="a4", description=f"Page size: {', '.join((*PAGE_SIZES, 'auto'))}"),
    fit: str = Query(default="fit", description=f"Fit mode: {', '.join(FIT_MODES)}"),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one image is required")

    for file in files:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not an image")

    images_bytes = [await f.read() for f in files]

    try:
        result = images_to_pdf(images_bytes, page_size=page_size, fit=fit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(
        content=result,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=output.pdf"}
    )


@app.post("/image/convert/batch")
async def image_convert_batch_endpoint(
    files: List[UploadFile],
    output_format: str = Query(description=f"Output format. One of: {', '.join(IMAGE_FORMAT_MAP)}"),
    width: Optional[int] = Query(default=None, description="Target width in pixels"),
    height: Optional[int] = Query(default=None, description="Target height in pixels"),
    scale: Optional[float] = Query(default=None, description="Scale by percentage e.g. 50 = 50%"),
    quality: int = Query(default=85, description="Quality 1–95 (applies to JPEG, WEBP, AVIF)"),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    for file in files:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not an image")

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            contents = await file.read()
            try:
                result, out_ext = convert_image(
                    contents,
                    output_format=output_format,
                    width=width,
                    height=height,
                    scale=scale,
                    quality=quality,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            out_filename = file.filename.rsplit(".", 1)[0] + f".{out_ext}"
            zf.writestr(out_filename, result)

    zip_buf.seek(0)
    return Response(
        content=zip_buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=converted_images.zip"}
    )


@app.post("/video/to-frames")
async def video_to_frames_endpoint(
    file: UploadFile,
    fps: Optional[float] = Query(default=None, description="Frames per second to extract. None = every frame"),
    quality: int = Query(default=3, description="PNG compression level 1–9 (lower = larger file, faster)"),
):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")

    input_ext = file.filename.rsplit(".", 1)[-1].lower()
    contents = await file.read()

    try:
        result = extract_video_frames(contents, input_ext=input_ext, fps=fps, quality=quality)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_frames.zip"
    return Response(
        content=result,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/video/compress")
async def video_compress_endpoint(
    file: UploadFile,
    crf: int = Query(default=28, description="Quality 0–63, higher = smaller file, lower quality"),
    preset: str = Query(default="medium", description=f"Encoding speed: {', '.join(VIDEO_PRESETS)}"),
):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")

    input_ext = file.filename.rsplit(".", 1)[-1].lower()
    contents = await file.read()

    try:
        result = compress_video(contents, input_ext=input_ext, crf=crf, preset=preset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    out_filename = file.filename.rsplit(".", 1)[0] + f"_compressed.{input_ext}"
    return Response(
        content=result,
        media_type=file.content_type,
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/watermark/text")
async def image_watermark_text_endpoint(
    file: UploadFile,
    text: str = Query(description="Text to overlay"),
    position: str = Query(default="bottom-right", description=f"Position: {', '.join(WATERMARK_POSITIONS)}"),
    font_size: int = Query(default=36, description="Font size in pixels"),
    color: str = Query(default="#ffffff", description="Hex color e.g. #ffffff"),
    opacity: int = Query(default=70, description="Opacity 0–100"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result = watermark_text(contents, text=text, position=position,
                                font_size=font_size, color=color, opacity=opacity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_watermarked.png"
    return Response(content=result, media_type="image/png",
                    headers={"Content-Disposition": f"attachment; filename={out_filename}"})


@app.post("/image/watermark/image")
async def image_watermark_image_endpoint(
    file: UploadFile,
    watermark: UploadFile,
    position: str = Query(default="bottom-right", description=f"Position: {', '.join(WATERMARK_POSITIONS)}"),
    scale: int = Query(default=20, description="Watermark width as % of base image width (1–100)"),
    opacity: int = Query(default=70, description="Opacity 0–100"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    if not watermark.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Watermark must be an image")

    contents = await file.read()
    wm_contents = await watermark.read()
    try:
        result = watermark_image(contents, wm_contents, position=position,
                                 scale=scale, opacity=opacity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_watermarked.png"
    return Response(content=result, media_type="image/png",
                    headers={"Content-Disposition": f"attachment; filename={out_filename}"})


@app.post("/video/watermark/text")
async def video_watermark_text_endpoint(
    file: UploadFile,
    text: str = Query(description="Text to overlay"),
    position: str = Query(default="bottom-right", description=f"Position: {', '.join(WATERMARK_POSITIONS)}"),
    font_size: int = Query(default=36, description="Font size in pixels"),
    color: str = Query(default="white", description="Color name or hex e.g. white, #ffffff"),
    opacity: float = Query(default=0.7, description="Opacity 0.0–1.0"),
):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")

    input_ext = file.filename.rsplit(".", 1)[-1].lower()
    contents = await file.read()
    try:
        result = watermark_text_video(contents, input_ext=input_ext, text=text,
                                      position=position, font_size=font_size,
                                      color=color, opacity=opacity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + f"_watermarked.{input_ext}"
    return Response(content=result, media_type=file.content_type,
                    headers={"Content-Disposition": f"attachment; filename={out_filename}"})


@app.post("/video/watermark/image")
async def video_watermark_image_endpoint(
    file: UploadFile,
    watermark: UploadFile,
    position: str = Query(default="bottom-right", description=f"Position: {', '.join(WATERMARK_POSITIONS)}"),
    scale: int = Query(default=20, description="Watermark width as % of video width (1–100)"),
    opacity: float = Query(default=0.7, description="Opacity 0.0–1.0"),
):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")
    if not watermark.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Watermark must be an image")

    input_ext = file.filename.rsplit(".", 1)[-1].lower()
    contents = await file.read()
    wm_contents = await watermark.read()
    try:
        result = watermark_image_video(contents, input_ext=input_ext,
                                       watermark_bytes=wm_contents, position=position,
                                       scale=scale, opacity=opacity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    out_filename = file.filename.rsplit(".", 1)[0] + f"_watermarked.{input_ext}"
    return Response(content=result, media_type=file.content_type,
                    headers={"Content-Disposition": f"attachment; filename={out_filename}"})


@app.post("/image/gif-to-video")
async def gif_to_video_endpoint(
    file: UploadFile,
    output_format: str = Query(default="mp4", description="Output format: mp4, webm, mov"),
    crf: Optional[int] = Query(default=23, description="Quality 0–51, lower = better"),
):
    if file.content_type != "image/gif":
        raise HTTPException(status_code=400, detail="File must be a GIF")

    allowed_formats = {"mp4", "webm", "mov"}
    if output_format.lower() not in allowed_formats:
        raise HTTPException(status_code=400, detail=f"Output format must be one of: {', '.join(allowed_formats)}")

    contents = await file.read()
    try:
        result, out_ext = convert_video(
            contents,
            input_ext="gif",
            output_format=output_format,
            crf=crf,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    out_filename = file.filename.rsplit(".", 1)[0] + f".{out_ext}"
    return Response(
        content=result,
        media_type=f"video/{out_ext}",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/blur-faces")
async def image_blur_faces_endpoint(
    file: UploadFile,
    blur_strength: int = Query(default=51, description="Effect intensity 1–99, higher = stronger"),
    min_face_size: int = Query(default=30, description="Minimum face size in pixels to detect"),
    style: str = Query(default="gaussian", description=f"Effect style: {', '.join(BLUR_STYLES)}"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result, face_count = blur_faces(
            contents,
            blur_strength=blur_strength,
            min_face_size=min_face_size,
            style=style,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + f"_{style}.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename={out_filename}",
            "X-Faces-Detected": str(face_count),
        }
    )


@app.post("/image/detect")
async def image_detect_endpoint(
    file: UploadFile,
    model_size: str = Query(default="n", description=f"Model size: {', '.join(YOLO_MODEL_SIZES)} (n=nano, s=small, m=medium)"),
    confidence: float = Query(default=0.5, description="Minimum confidence threshold 0.0–1.0"),
    show_labels: bool = Query(default=True, description="Draw class name on each box"),
    show_confidence: bool = Query(default=True, description="Draw confidence % on each box"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result, detections = detect_objects(
            contents,
            model_size=model_size,
            confidence=confidence,
            show_labels=show_labels,
            show_confidence=show_confidence,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_detected.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename={out_filename}",
            "X-Detections-Count": str(len(detections)),
        }
    )


@app.post("/video/detect")
async def video_detect_endpoint(
    file: UploadFile,
    model_size: str = Query(default="n", description=f"Model size: {', '.join(YOLO_MODEL_SIZES)} (n=nano, s=small, m=medium)"),
    confidence: float = Query(default=0.5, description="Minimum confidence threshold 0.0–1.0"),
    show_labels: bool = Query(default=True, description="Draw class name on each box"),
    show_confidence: bool = Query(default=True, description="Draw confidence % on each box"),
):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")

    input_ext = file.filename.rsplit(".", 1)[-1].lower()
    contents  = await file.read()
    try:
        result = detect_objects_video(
            contents,
            input_ext=input_ext,
            model_size=model_size,
            confidence=confidence,
            show_labels=show_labels,
            show_confidence=show_confidence,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    out_filename = file.filename.rsplit(".", 1)[0] + "_detected.mp4"
    return Response(
        content=result,
        media_type="video/mp4",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/detect")
async def image_detect_endpoint(
    file: UploadFile,
    model_size: str = Query(default="n", description=f"Model size: {', '.join(YOLO_MODEL_SIZES)} (n=fastest, m=most accurate)"),
    confidence: float = Query(default=0.5, description="Minimum confidence threshold 0.0–1.0"),
    show_labels: bool = Query(default=True, description="Show class label on each box"),
    show_confidence: bool = Query(default=True, description="Show confidence % on each box"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result, detections = detect_objects(
            contents,
            model_size=model_size,
            confidence=confidence,
            show_labels=show_labels,
            show_confidence=show_confidence,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + "_detected.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename={out_filename}",
            "X-Detections-Count": str(len(detections)),
        }
    )


@app.post("/video/detect")
async def video_detect_endpoint(
    file: UploadFile,
    model_size: str = Query(default="n", description=f"Model size: {', '.join(YOLO_MODEL_SIZES)} (n=fastest, m=most accurate)"),
    confidence: float = Query(default=0.5, description="Minimum confidence threshold 0.0–1.0"),
    show_labels: bool = Query(default=True, description="Show class label on each box"),
    show_confidence: bool = Query(default=True, description="Show confidence % on each box"),
):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="File must be a video (mp4, mov, avi, webm)")

    input_ext = file.filename.rsplit(".", 1)[-1].lower()
    contents  = await file.read()
    try:
        result = detect_objects_video(
            contents,
            input_ext=input_ext,
            model_size=model_size,
            confidence=confidence,
            show_labels=show_labels,
            show_confidence=show_confidence,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    out_filename = file.filename.rsplit(".", 1)[0] + "_detected.mp4"
    return Response(
        content=result,
        media_type="video/mp4",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/image/upscale")
async def image_upscale_endpoint(
    file: UploadFile,
    scale: int = Query(default=2, description=f"Upscale factor: {', '.join(map(str, UPSCALE_FACTORS))}"),
    method: str = Query(default="lanczos", description=f"Method: {', '.join(UPSCALE_METHODS)}"),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    try:
        result = upscale_image(contents, scale=scale, method=method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    out_filename = file.filename.rsplit(".", 1)[0] + f"_{scale}x_{method}.png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.get("/models")
async def list_models():
    return {"models": AVAILABLE_MODELS}


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    import uvicorn
    import webbrowser
    import threading
    def _open(): webbrowser.open("http://localhost:8000")
    threading.Timer(1.5, _open).start()
    uvicorn.run("snapconvert.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
