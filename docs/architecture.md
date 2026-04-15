# 아키텍처

## 개요

Social Distance Monitor는 YOLOv8 기반 사람 감지와 거리 위반 판정을 실시간으로 수행하고, 결과를 웹 UI에서 시각화하는 시스템입니다. 백엔드(Python / FastAPI)와 프론트엔드(Vite + React + TypeScript)가 분리되어 있으며, 영상 처리는 백엔드의 단일 워커 스레드에서 수행됩니다.

## 전체 구성

```
┌────────────────────────┐             ┌────────────────────────────────┐
│       Browser          │             │          Backend               │
│  (Vite dev / static)   │             │          (FastAPI)             │
│                        │             │                                │
│  ┌──────────────────┐  │   HTTP/WS   │  ┌──────────────────────────┐  │
│  │ React Components │◀─┼─────────────┼─▶│    REST / WS handlers    │  │
│  │                  │  │             │  └───────────┬──────────────┘  │
│  │  VideoStream     │  │             │              │                 │
│  │  StatsPanel      │  │             │              ▼                 │
│  │  Controls        │  │             │  ┌──────────────────────────┐  │
│  │  SourceSelector  │  │             │  │     VideoProcessor       │  │
│  └──────────────────┘  │             │  │     (worker thread)      │  │
│                        │             │  └───┬─────────┬─────────┬──┘  │
│  ┌──────────────────┐  │             │      │         │         │     │
│  │ zustand store    │  │             │      ▼         ▼         ▼     │
│  │ WS hook          │  │             │  Detector  Distance  Visualizer│
│  └──────────────────┘  │             │   (YOLO)   Monitor   (OpenCV)  │
└────────────────────────┘             └────────────────────────────────┘
        ▲                                            ▲
        │                                            │
        └── MJPEG /stream (multipart/x-mixed-replace)┘
```

## 계층 분리

### 1. Domain Core (순수 비즈니스 로직)

GUI나 네트워크와 독립적으로 동작하는 순수 클래스들.

- **`detector.YoloDetector`**
  - `ultralytics.YOLO` 래핑
  - `torch.cuda.is_available()`로 device 자동 선택
  - `detect(frame, conf_threshold)` → `(boxes, confidences, box_centers)`
  - 사람 클래스(`classes=0`)만 필터링
- **`distance_monitor.DistanceMonitor`**
  - 중심점 리스트를 받아 모든 쌍을 O(n²/2)로 검사
  - 제곱 비교로 `sqrt` 제거
  - 인덱스 쌍 `(i, j)` 와 고유 위반 인원 수 반환
- **`visualizer.Visualizer`**
  - 인덱스 쌍 기반으로 위반 연결선과 박스 색상 결정
  - 좌상단에 위반 인원 수 오버레이

### 2. Runtime Orchestrator

- **`video_processor.VideoProcessor`**
  - 백그라운드 데몬 스레드에서 프레임 루프 실행
  - **공유 상태**: 최신 JPEG 바이트, 통계 dict, 설정 dict, 에러, 일시정지 플래그
  - **동기화**: `threading.Lock`으로 dict/bytes 교체, `threading.Event`로 stop/pause/first-frame ready
  - **원자적 설정 스냅샷**: 루프 시작 시 `dict(self._config)` 복사 → 프레임 중간에 값이 섞이지 않음
  - **소스 교체**: `_pending_source` 플래그 → 루프 내에서 안전하게 캡처 교체 (webcam busy 회피용 300ms 대기)
  - **소스 종류 해석**: `default` / `upload` / `webcam` / `file`
  - **예외 안전성**: 루프 전체 `try/except` → `_error` 저장, `/api/stats` 응답에 노출

### 3. Transport (HTTP / WebSocket)

- **`server.py`** (FastAPI)
  - `lifespan` 컨텍스트로 `VideoProcessor` 기동·종료
  - CORS 허용 (`localhost:5173`)
  - REST 엔드포인트: stats / config / source / upload / control
  - `/stream` → `StreamingResponse`로 MJPEG (`multipart/x-mixed-replace`)
  - `/ws/events` → 30Hz 통계 브로드캐스트, 단일 사용자 정책(신규 연결 시 기존 연결 close)
  - `/api/upload` → 1MB 청크 스트리밍 저장, 확장자 화이트리스트, UUID 파일명, 500MB 상한

### 4. Presentation (프론트엔드)

- **Vite + React + TypeScript + Tailwind CSS**
- **컴포넌트**
  - `VideoStream`: `<img src="/stream?k=...">` — MJPEG를 이미지로 렌더
  - `StatsPanel`: WebSocket 수신 통계를 3개 카드로 표시, Live 인디케이터
  - `Controls`: 슬라이더(디바운스 300ms) + Play/Pause/Stop 버튼
  - `SourceSelector`: 3-way 라디오 (Default / Upload / Webcam), 파일 업로드 → `upload_id` → `set_source`
- **상태 관리**: `zustand`
  - `stats`, `config`, `status`, `streamKey`, `wsConnected`
- **훅**
  - `useStatsWebSocket`: `/ws/events` 연결, 실패 시 1초 후 재연결
  - `useDebouncedConfigPush`: 슬라이더 변경을 300ms 디바운스로 `POST /api/config`
- **개발 프록시**: Vite가 `/api`, `/stream`, `/ws`를 `localhost:8000`으로 포워딩 → CORS·경로 고민 제거

## 데이터 흐름

### 프레임 파이프라인

```
VideoCapture.read()
   ▼
cv2.resize(640×480)
   ▼
YoloDetector.detect(conf_threshold)         ← 설정 스냅샷
   ▼
DistanceMonitor.check_distances(safe_dist)  ← 설정 스냅샷
   ▼
Visualizer.draw_results(...)
   ▼
cv2.imencode('.jpg', quality=70)
   ▼
lock → _latest_jpeg, _stats 갱신
   ▼
stream_jpeg() / WebSocket 브로드캐스트
```

### 설정 변경

```
UI Slider onChange
   ▼ (React setState)
local state
   ▼ (300ms debounce)
POST /api/config
   ▼
processor.update_config()  → _state_lock 아래 dict 갱신
   ▼
다음 프레임 루프가 새 값 스냅샷
```

### 소스 전환 (업로드 경로)

```
사용자 파일 선택
   ▼
POST /api/upload (multipart)
   ▼ (1MB 청크 스트리밍)
uploads/<uuid>.<ext> 저장
   ▼
{upload_id} 반환
   ▼
POST /api/source {kind:"upload", value:upload_id}
   ▼
processor._pending_source 플래그 설정
   ▼
루프 내: 기존 cap.release() → 300ms 대기 → 새 cap 오픈
   ▼
프론트: bumpStream() → <img> src 쿼리 갱신 → MJPEG 재연결
```

## 동시성 모델

- **단일 워커 스레드**: VideoProcessor가 소유한 데몬 스레드 1개가 영상 처리 전담
- **asyncio와의 경계**: FastAPI 핸들러는 `run_in_threadpool` 없이 즉시 메모리(lock 아래)만 읽고 응답 → 이벤트 루프 차단 없음
- **WebSocket**: `asyncio.sleep(1/30)`으로 30Hz 폴링, 단일 활성 연결
- **MJPEG 스트림**: 동기 제너레이터가 `time.sleep(1/30)`으로 페이스 조절, `GeneratorExit` 처리

## 확장 고려 사항

- **다중 사용자**: 현재 전역 단일 프로세서. 사용자별 세션이 필요하면 프로세서 풀 + 세션 토큰 필요
- **WebRTC**: MJPEG는 ~300ms 지연. 저지연이 필요하면 aiortc 기반 WebRTC 전환
- **실세계 거리**: 현재 픽셀 단위. 호모그래피 변환으로 bird's-eye view 좌표 변환 시 실제 미터 단위 가능
- **지표 저장**: 통계를 SQLite/TSDB에 기록하면 시계열 대시보드 구성 가능
- **정적 배포**: `frontend/dist`를 FastAPI `StaticFiles`로 마운트하면 단일 프로세스로 통합 배포 가능

## 파일 매핑

| 계층 | 파일 |
|---|---|
| Domain | `backend/detector.py`, `backend/distance_monitor.py`, `backend/visualizer.py` |
| Orchestrator | `backend/video_processor.py` |
| Transport | `backend/server.py` |
| Config | `backend/config.py` |
| Legacy GUI | `backend/main.py` |
| Presentation | `frontend/src/**` |
