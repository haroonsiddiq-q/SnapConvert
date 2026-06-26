from fastapi import FastAPI, UploadFile, HTTPException, Query
from fastapi.responses import Response
from snapconvert.image_background_removal import remove_background, AVAILABLE_MODELS
from snapconvert.image_background_color import apply_background_color
from snapconvert.image_background_replace import replace_background
import zipfile
import io

app = FastAPI(title="SnapConvert")


@app.post("/remove-bg")
async def remove_bg_endpoint(
    file: UploadFile,
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=True),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    result = remove_background(contents, model=model, alpha_matting=alpha_matting)

    out_filename = file.filename.rsplit(".", 1)[0] + ".png"
    return Response(
        content=result,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={out_filename}"}
    )


@app.post("/remove-bg/batch")
async def remove_bg_batch(
    files: list[UploadFile],
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=True),
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
            result = remove_background(contents, model=model, alpha_matting=alpha_matting)
            out_filename = file.filename.rsplit(".", 1)[0] + ".png"
            zf.writestr(out_filename, result)

    zip_buf.seek(0)
    return Response(
        content=zip_buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=removed_backgrounds.zip"}
    )


@app.post("/apply-bg-color")
async def apply_bg_color_endpoint(
    file: UploadFile,
    color: str = Query(default="#ffffff", description="Hex color e.g. #ff0000"),
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=True),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    removed = remove_background(contents, model=model, alpha_matting=alpha_matting)

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


@app.post("/replace-bg")
async def replace_bg_endpoint(
    file: UploadFile,
    background: UploadFile,
    model: str = Query(default="u2net", enum=AVAILABLE_MODELS),
    alpha_matting: bool = Query(default=True),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Subject file must be an image")
    if not background.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Background file must be an image")

    contents = await file.read()
    bg_contents = await background.read()

    removed = remove_background(contents, model=model, alpha_matting=alpha_matting)
    result = replace_background(removed, bg_contents)

    out_filename = file.filename.rsplit(".", 1)[0] + ".png"
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
    uvicorn.run("snapconvert.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
