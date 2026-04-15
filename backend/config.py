from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

YOLOV8_MODEL_PATH = str(BASE_DIR / "yolov8n.pt")
VIDEO_PATH = str(BASE_DIR / "small.mp4")
OUTPUT_PATH = str(BASE_DIR / "output.avi")

SAFE_DISTANCE = 75.0
CONFIDENCE_THRESHOLD = 0.5

UPLOAD_DIR = BASE_DIR / "uploads"
MAX_UPLOAD_MB = 500
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
