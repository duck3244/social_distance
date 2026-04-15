import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import (
    ALLOWED_VIDEO_EXT,
    CONFIDENCE_THRESHOLD,
    MAX_UPLOAD_MB,
    SAFE_DISTANCE,
    UPLOAD_DIR,
    VIDEO_PATH,
    YOLOV8_MODEL_PATH,
)
from video_processor import VideoProcessor

logger = logging.getLogger(__name__)

processor: Optional[VideoProcessor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global processor
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    processor = VideoProcessor(
        model_path=YOLOV8_MODEL_PATH,
        default_source=VIDEO_PATH,
        safe_distance=SAFE_DISTANCE,
        conf_threshold=CONFIDENCE_THRESHOLD,
    )
    processor.start()
    logger.info("VideoProcessor started")
    try:
        yield
    finally:
        logger.info("Shutting down VideoProcessor")
        processor.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigPayload(BaseModel):
    safe_distance: Optional[float] = None
    conf_threshold: Optional[float] = None


class SourcePayload(BaseModel):
    kind: Literal["default", "upload", "webcam", "file"]
    value: Optional[str] = None


class ControlPayload(BaseModel):
    action: Literal["play", "pause", "stop"]


@app.get("/api/stats")
def get_stats():
    return {
        "stats": processor.get_stats(),
        "config": processor.get_config(),
        "source": processor.get_source(),
    }


@app.post("/api/config")
def post_config(payload: ConfigPayload):
    cfg = processor.update_config(
        safe_distance=payload.safe_distance,
        conf_threshold=payload.conf_threshold,
    )
    return {"config": cfg}


@app.post("/api/source")
def post_source(payload: SourcePayload):
    processor.set_source(payload.kind, payload.value)
    return {"ok": True}


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXT:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported extension: {ext}")

    upload_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{upload_id}{ext}"
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024

    # 이전 업로드 정리 (단일 사용자 정책)
    for old in UPLOAD_DIR.glob("*"):
        if old.is_file():
            try:
                old.unlink()
            except OSError:
                pass

    written = 0
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    f.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413,
                                        detail=f"File exceeds {MAX_UPLOAD_MB}MB limit")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    return {"upload_id": upload_id, "filename": filename, "size": written}


@app.post("/api/control")
def post_control(payload: ControlPayload):
    if payload.action == "play":
        processor.resume()
    elif payload.action == "pause":
        processor.pause()
    elif payload.action == "stop":
        processor.pause()
    return {"ok": True, "action": payload.action}


@app.get("/stream")
def stream():
    return StreamingResponse(
        processor.stream_jpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


_ws_lock = asyncio.Lock()
_active_ws: Optional[WebSocket] = None


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    global _active_ws
    await ws.accept()
    async with _ws_lock:
        if _active_ws is not None:
            try:
                await _active_ws.close()
            except Exception:
                pass
        _active_ws = ws
    try:
        while True:
            payload = {
                "stats": processor.get_stats(),
                "config": processor.get_config(),
            }
            await ws.send_json(payload)
            await asyncio.sleep(1 / 30)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        async with _ws_lock:
            if _active_ws is ws:
                _active_ws = None
