# SnapConvert

A local, browser-based toolkit for image and video processing — background removal, format conversion, filters, pixelation, watermarking, object detection, upscaling, and more. Runs entirely on your own machine via a FastAPI backend with a simple web UI.

> ⚠️ **AI-assisted / "vibe-coded" project.** This is a personal tool built primarily through AI-assisted ("vibe-coded") development. It hasn't been through a formal security review or production hardening, and some parts of the code and this README were written or scaffolded with AI assistance. It's intended for personal/local use as a set of handy tools — treat it accordingly.

## Features

- **Background removal** — image & video, with color replacement and background replacement
- **Format conversion** — image & video, including batch conversion
- **Crop & transform** — manual crop, smart (subject-aware) crop, rotate, flip
- **Filters** — brightness, contrast, saturation, sharpness
- **Pixelate** — retro pixel-art filter with adjustable block size and color palette
- **EXIF tools** — read and strip metadata
- **Watermarking** — text and image watermarks, for both images and video
- **Image → PDF** — combine images into a PDF
- **Video tools** — extract frames, compress, GIF-to-video
- **Face blurring**
- **Object detection** — image & video (YOLO-based)
- **Upscaling** — Lanczos or Real-ESRGAN AI upscaling

## Requirements

- Python 3.9
- [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync
```

This installs all dependencies, including ML models for background removal, object detection, and upscaling (larger downloads happen on first use).

## Running

```bash
uv run uvicorn snapconvert.main:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** in your browser.

### Windows: desktop shortcut (one-click launch)

For convenience, this repo includes:

- `start_snapconvert.bat` — starts the server and opens the app in your browser
- `start_snapconvert_silent.vbs` — same, but with no visible console window
- `create_desktop_shortcut.ps1` — creates a Desktop shortcut pointing at the silent launcher

Run once from the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1
```

This adds a **SnapConvert** icon to your Desktop. Double-click it any time to launch the app straight to your browser.

## Notes

- All processing happens locally — files are not uploaded anywhere.
- The server keeps running in the background after you close the browser tab; close it manually via Task Manager (or your OS's process manager) when you're done.