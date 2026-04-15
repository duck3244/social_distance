# Backend

FastAPI + YOLOv8 기반 사회적 거리두기 모니터링 백엔드.

## 구성 요소

| 파일 | 역할 |
|---|---|
| `server.py` | FastAPI 엔트리. REST/WebSocket 엔드포인트, MJPEG 스트리밍, 비디오 업로드 |
| `video_processor.py` | 백그라운드 워커 스레드. 프레임 루프, 공유 상태, 원자적 설정, 소스 교체 |
| `detector.py` | `ultralytics.YOLO` 래퍼. CUDA 자동 감지, 사람(class=0)만 필터링 |
| `distance_monitor.py` | 중심점 쌍 거리 계산 (O(n²/2), 제곱 비교) |
| `visualizer.py` | OpenCV 기반 박스/연결선/텍스트 오버레이 |
| `config.py` | 경로, 기본값, 업로드 정책 |
| `main.py` | 로컬 OpenCV GUI 런처 (회귀 테스트용) |
| `yolov8n.pt` | YOLOv8 nano 사전 학습 모델 |
| `small.mp4` | 기본 샘플 영상 |
| `uploads/` | 런타임 업로드 저장 디렉토리 (gitignore) |

## 요구 사항

- Python 3.10+
- NVIDIA GPU 권장 (CPU도 동작하지만 느림)
- 웹캠 기능은 `/dev/video*` 접근 권한 필요 (Linux)

## 설치

```bash
pip install -r requirements.txt
```

주요 의존성:
- `fastapi`, `uvicorn[standard]`, `python-multipart`, `websockets`
- `ultralytics`, `opencv-python`, `numpy`
- `torch`, `torchvision`, `torchaudio`

## 실행

### 웹 서버 모드 (권장)

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

기동 후 브라우저 또는 프론트엔드(`http://localhost:5173`)에서 접근.

- 개발 중에는 `--reload` 사용을 피하세요. 모듈 재로딩 시 VideoProcessor 스레드·캡처 핸들이 누수될 수 있습니다.

### 로컬 OpenCV GUI 모드 (회귀용)

웹 UI 없이 기존 `cv2.imshow` 기반으로 실행:

```bash
python main.py
```

`q` 키로 종료합니다.

## API

### REST

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET  | `/api/stats`   | 최신 통계 + 현재 설정 + 소스 정보 |
| POST | `/api/config`  | `{safe_distance?, conf_threshold?}` 런타임 변경 |
| POST | `/api/source`  | `{kind, value?}` 소스 전환 |
| POST | `/api/upload`  | multipart 비디오 업로드 |
| POST | `/api/control` | `{action: "play"\|"pause"\|"stop"}` |
| GET  | `/stream`      | MJPEG 스트림 (`multipart/x-mixed-replace`) |
| WS   | `/ws/events`   | 30Hz 통계 푸시 |

### Source kinds

```jsonc
{ "kind": "default" }                          // config.VIDEO_PATH
{ "kind": "upload",  "value": "<upload_id>" }  // /api/upload 결과
{ "kind": "webcam",  "value": "0" }             // /dev/video0
{ "kind": "file",    "value": "/abs/path" }     // 로컬 임의 경로
```

### 업로드 정책

- 최대 크기: 500MB (`config.MAX_UPLOAD_MB`)
- 허용 확장자: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`
- UUID 파일명 저장 (path traversal 차단)
- 1MB 청크 스트리밍 (OOM 방지)
- 새 업로드 시 이전 파일 자동 삭제 (단일 사용자 정책)

## 설정 (`config.py`)

```python
SAFE_DISTANCE = 75.0          # 픽셀 단위 안전 거리
CONFIDENCE_THRESHOLD = 0.5    # YOLO 신뢰도 임계값
MAX_UPLOAD_MB = 500
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
```

런타임에는 UI 슬라이더로 `SAFE_DISTANCE`와 `CONFIDENCE_THRESHOLD`를 즉시 변경할 수 있습니다 (300ms 디바운스).

## 동시성 모델

- **단일 워커 스레드**: `VideoProcessor`가 소유한 데몬 스레드 1개가 영상 처리 전담
- **락**: `threading.Lock`으로 최신 JPEG/통계/설정 공유
- **이벤트**: `stop_event`, `pause_event`, `frame_ready`로 제어
- **FastAPI 핸들러**: lock 아래 메모리만 읽고 응답 → 이벤트 루프 비차단
- **WebSocket**: 30Hz 통계 폴링, 단일 활성 연결만 유지

## VideoProcessor 내부 동작

1. 데몬 스레드 시작 → 루프 진입
2. 매 반복 시점에 `_pending_source` 플래그 확인 → 있으면 캡처 교체 (300ms 대기로 웹캠 busy 회피)
3. `_pause_event` 확인 → 일시정지 시 sleep
4. `cap.read()` → 실패 시 파일이면 0번 프레임으로 리셋
5. `cv2.resize(640, 480)` 강제 (MJPEG 대역폭 일관성)
6. `_state_lock` 아래 설정 스냅샷(`dict(self._config)`) → 프레임 중간 값 혼합 방지
7. `Detector → DistanceMonitor → Visualizer` 파이프라인
8. `cv2.imencode('.jpg', quality=70)` → 락 아래 `_latest_jpeg`, `_stats` 갱신
9. `_frame_ready.set()` → MJPEG 제너레이터 대기 해제

## 주의 사항

- 거리 측정은 **픽셀 단위**입니다. 카메라 각도·원근에 따라 의미가 달라집니다.
- 첫 프레임 준비 전 `/stream` 요청은 최대 5초간 대기합니다.
- 웹캠 소스 교체 시 OS 핸들 해제를 위해 300ms 대기합니다.
- 서버 종료 시 `uploads/` 파일은 유지됩니다 (디버깅 편의).
- GPU 드라이버/CUDA 미설치 환경에서는 자동으로 CPU로 fallback 합니다.

## 자세한 아키텍처

루트의 [`docs/architecture.md`](../docs/architecture.md) 와 [`docs/uml.md`](../docs/uml.md) 참조.
