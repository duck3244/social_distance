import logging
import threading
import time
from typing import Iterator, Literal, Optional

import cv2

from config import UPLOAD_DIR
from detector import YoloDetector
from distance_monitor import DistanceMonitor
from visualizer import Visualizer

logger = logging.getLogger(__name__)

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
JPEG_QUALITY = 70
MJPEG_BOUNDARY = b"--frame"


class VideoProcessor:
    def __init__(self, model_path: str, default_source: str,
                 safe_distance: float, conf_threshold: float):
        self._detector = YoloDetector(model_path)
        self._distance_monitor = DistanceMonitor(safe_distance)
        self._visualizer = Visualizer()

        self._state_lock = threading.Lock()
        self._config = {
            "safe_distance": float(safe_distance),
            "conf_threshold": float(conf_threshold),
        }
        self._latest_jpeg: Optional[bytes] = None
        self._stats = {"frame_id": 0, "people": 0, "unsafe": 0, "fps": 0.0}
        self._error: Optional[str] = None

        self._default_source = default_source
        self._pending_source: Optional[tuple[str, object]] = None
        self._current_source: tuple[str, object] = ("default", None)

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()  # set = paused
        self._frame_ready = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------- lifecycle -------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="VideoProcessor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()

    # ------------- config / source -------------

    def update_config(self, safe_distance: Optional[float] = None,
                      conf_threshold: Optional[float] = None) -> dict:
        with self._state_lock:
            if safe_distance is not None:
                self._config["safe_distance"] = float(safe_distance)
            if conf_threshold is not None:
                self._config["conf_threshold"] = float(conf_threshold)
            return dict(self._config)

    def set_source(self, kind: Literal["file", "webcam"], value) -> None:
        with self._state_lock:
            self._pending_source = (kind, value)

    def get_config(self) -> dict:
        with self._state_lock:
            return dict(self._config)

    def get_source(self) -> dict:
        with self._state_lock:
            kind, value = self._current_source
            return {"kind": kind, "value": value}

    # ------------- readers -------------

    def get_stats(self) -> dict:
        with self._state_lock:
            out = dict(self._stats)
            out["error"] = self._error
            out["paused"] = self._pause_event.is_set()
            return out

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self._state_lock:
            return self._latest_jpeg

    def stream_jpeg(self) -> Iterator[bytes]:
        try:
            # 첫 프레임 대기 (최대 5초)
            if not self._frame_ready.wait(timeout=5.0):
                return
            while not self._stop_event.is_set():
                jpeg = self.get_latest_jpeg()
                if jpeg is None:
                    time.sleep(0.02)
                    continue
                yield (MJPEG_BOUNDARY + b"\r\n"
                       b"Content-Type: image/jpeg\r\n"
                       b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                       + jpeg + b"\r\n")
                time.sleep(1 / 30)
        except (GeneratorExit, ConnectionError):
            logger.info("MJPEG client disconnected")
            return

    # ------------- internal -------------

    def _resolve_source(self, kind: str, value) -> object:
        if kind == "default":
            return self._default_source
        if kind == "upload":
            matches = list(UPLOAD_DIR.glob(f"{value}.*"))
            if not matches:
                return None
            return str(matches[0])
        if kind == "webcam":
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
        if kind == "file":
            return str(value)
        return None

    def _open_capture(self, kind: str, value) -> Optional[cv2.VideoCapture]:
        resolved = self._resolve_source(kind, value)
        if resolved is None:
            return None
        if isinstance(resolved, int):
            cap = cv2.VideoCapture(resolved)
        else:
            cap = cv2.VideoCapture(resolved)
        if not cap.isOpened():
            return None
        return cap

    def _run(self) -> None:
        try:
            self._loop()
        except Exception as e:
            logger.exception("VideoProcessor loop crashed")
            with self._state_lock:
                self._error = f"{type(e).__name__}: {e}"

    def _loop(self) -> None:
        kind, value = self._current_source
        cap = self._open_capture(kind, value)
        if cap is None:
            with self._state_lock:
                self._error = f"Could not open source: {kind}={value}"
            return

        fps_ema = 0.0
        last_tick = time.time()
        frame_id = 0

        while not self._stop_event.is_set():
            # 소스 교체 요청 처리
            with self._state_lock:
                pending = self._pending_source
                self._pending_source = None
            if pending is not None:
                cap.release()
                time.sleep(0.3)
                new_cap = self._open_capture(*pending)
                if new_cap is None:
                    with self._state_lock:
                        self._error = f"Could not open source: {pending}"
                    # fallback: 원래 소스 다시 열기
                    cap = self._open_capture(*self._current_source)
                    if cap is None:
                        return
                else:
                    cap = new_cap
                    with self._state_lock:
                        self._current_source = pending
                        self._error = None

            if self._pause_event.is_set():
                time.sleep(0.05)
                continue

            grabbed, frame = cap.read()
            if not grabbed:
                # 파일 끝 → 루프 (webcam 제외)
                if self._current_source[0] != "webcam":
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.05)
                continue

            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # 원자적 설정 스냅샷
            with self._state_lock:
                cfg = dict(self._config)
            self._distance_monitor.safe_distance = cfg["safe_distance"]
            self._distance_monitor._safe_distance_sq = cfg["safe_distance"] ** 2

            boxes, confs, centers = self._detector.detect(frame, cfg["conf_threshold"])
            unsafe_pairs, unsafe_count = self._distance_monitor.check_distances(boxes, centers)
            out_frame = self._visualizer.draw_results(frame, boxes, confs, centers, unsafe_pairs, unsafe_count)

            ok, buf = cv2.imencode(".jpg", out_frame,
                                   [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if not ok:
                continue

            now = time.time()
            dt = now - last_tick
            last_tick = now
            inst_fps = 1.0 / dt if dt > 0 else 0.0
            fps_ema = inst_fps if fps_ema == 0 else (0.9 * fps_ema + 0.1 * inst_fps)
            frame_id += 1

            with self._state_lock:
                self._latest_jpeg = buf.tobytes()
                self._stats = {
                    "frame_id": frame_id,
                    "people": len(boxes),
                    "unsafe": unsafe_count,
                    "fps": round(fps_ema, 1),
                }
            self._frame_ready.set()

        cap.release()
