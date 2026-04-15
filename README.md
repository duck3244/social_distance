# Social Distance Monitor

![Demo](demo.png)

YOLOv8 기반 실시간 사회적 거리두기 모니터링 시스템. FastAPI 백엔드 + Vite/React 프론트엔드로 구성되어 있으며, 영상 파일 업로드·웹캠·기본 샘플 영상을 실시간으로 분석해 사람 간 거리를 감시합니다.

## 기능

- YOLOv8 기반 사람 감지 (CUDA GPU 자동 사용)
- 안전 거리 위반 쌍 시각화 (빨간 박스·연결선)
- 실시간 통계: People / Unsafe / FPS
- 런타임 설정 변경: Safe distance, Confidence threshold (슬라이더)
- 소스 전환: 기본 영상 / 비디오 업로드 / 웹캠
- MJPEG 스트리밍 + WebSocket 통계 푸시
- Play / Pause / Stop 컨트롤

## 아키텍처

```
[Browser]
    │
    │  Vite dev (5173)  ── proxy ──▶  FastAPI (8000)
    │                                       │
    │◀── MJPEG /stream ─────────────────────┤
    │◀── WS /ws/events (stats) ─────────────┤
    │──▶ /api/{stats,config,source,upload,control}
                                            │
                                      VideoProcessor (thread)
                                            │
                            Detector ─ DistanceMonitor ─ Visualizer
```

- **VideoProcessor**: 백그라운드 스레드에서 프레임 루프 실행, 최신 JPEG·통계를 락 아래 공유, 원자적 설정 스냅샷, 소스 교체는 루프 내에서 수행
- **MJPEG**: `multipart/x-mixed-replace` 응답을 `<img src="/stream">`로 재생
- **WebSocket**: 30Hz로 통계 브로드캐스트, 단일 사용자 가정 (신규 연결 시 기존 연결 종료)

## 디렉토리 구조

```
social_distance/
├── backend/
│   ├── server.py              # FastAPI 엔트리 (lifespan, CORS, MJPEG, WS)
│   ├── video_processor.py     # 스레드 루프, 공유 상태, 소스 교체
│   ├── detector.py            # YOLOv8 래퍼
│   ├── distance_monitor.py    # 쌍 거리 계산
│   ├── visualizer.py          # OpenCV 오버레이
│   ├── config.py              # 경로, 기본값, 업로드 정책
│   ├── main.py                # 로컬 OpenCV GUI 런처 (회귀용)
│   ├── requirements.txt
│   ├── yolov8n.pt
│   ├── small.mp4              # 기본 샘플 영상
│   └── uploads/               # 런타임 업로드 저장 (gitignore)
├── frontend/
│   ├── vite.config.ts         # /api, /stream, /ws 프록시
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx
│       ├── components/        # VideoStream, StatsPanel, Controls, SourceSelector
│       ├── hooks/             # useWebSocket, useDebouncedConfig
│       ├── store/useAppStore.ts
│       └── lib/api.ts
└── README.md
```

## 요구 사항

- Python 3.10+
- Node.js 18+
- NVIDIA GPU (선택, CPU로도 동작하지만 느림)
- 웹캠 기능은 `/dev/video*` 접근 권한 필요 (Linux)

## 설치

### 백엔드
```bash
cd backend
pip install -r requirements.txt
```

### 프론트엔드
```bash
cd frontend
npm install
```

## 실행

### 개발 모드 (권장)
터미널 2개를 사용합니다.

**백엔드**
```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000
```

**프론트엔드**
```bash
cd frontend
npm run dev
```

브라우저에서 `http://localhost:5173` 접속.

### 로컬 OpenCV GUI (회귀 테스트용)
웹 UI 없이 기존 `cv2.imshow` 기반으로 실행하려면:
```bash
cd backend
python main.py
```
`q` 키로 종료.

## API

### REST

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET  | `/api/stats`   | 최신 통계 + 현재 설정 + 소스 정보 |
| POST | `/api/config`  | `{safe_distance?, conf_threshold?}` 런타임 변경 |
| POST | `/api/source`  | `{kind, value?}` 소스 전환 |
| POST | `/api/upload`  | multipart 비디오 업로드, `{upload_id, filename, size}` 반환 |
| POST | `/api/control` | `{action: "play"\|"pause"\|"stop"}` |
| GET  | `/stream`      | MJPEG 스트림 (`multipart/x-mixed-replace`) |
| WS   | `/ws/events`   | 30Hz 통계 푸시 |

### Source kinds

```jsonc
{ "kind": "default" }                             // 기본 샘플 영상
{ "kind": "upload",  "value": "<upload_id>" }     // /api/upload 결과 사용
{ "kind": "webcam",  "value": "0" }                // /dev/video0
```

### 업로드 정책
- 최대 크기: 500MB (`config.MAX_UPLOAD_MB`)
- 허용 확장자: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`
- UUID 기반 파일명 저장 (path traversal 차단)
- 1MB 청크 스트리밍 (OOM 방지)
- 신규 업로드 시 이전 파일 자동 삭제 (단일 사용자 정책)

## 설정

`backend/config.py`에서 기본값 조정:

```python
SAFE_DISTANCE = 75.0         # 픽셀 단위 안전 거리
CONFIDENCE_THRESHOLD = 0.5   # YOLO 신뢰도 임계값
MAX_UPLOAD_MB = 500
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
```

런타임 중에는 UI 슬라이더로 `SAFE_DISTANCE`와 `CONFIDENCE_THRESHOLD`를 즉시 변경할 수 있습니다 (300ms 디바운스).

## 주의 사항

- 거리 측정은 **픽셀 단위**입니다. 카메라 각도·원근에 따라 의미가 달라지므로, 엄밀한 측정을 위해서는 호모그래피 변환을 통한 bird's-eye view 보정이 필요합니다.
- 첫 프레임 준비 전에는 `/stream`이 최대 5초간 대기합니다.
- 웹캠 소스 교체 시 OS가 디바이스 핸들을 해제할 시간을 주기 위해 300ms 대기합니다.
- 서버 종료 시 `uploads/`는 유지됩니다 (디버깅 용이).

## 라이선스

LICENSE 파일 참조.
