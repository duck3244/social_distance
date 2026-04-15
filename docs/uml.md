# UML 다이어그램

Mermaid 기반 다이어그램 모음. GitHub / VS Code / IntelliJ에서 바로 렌더링됩니다.

## 1. 컴포넌트 다이어그램

```mermaid
flowchart LR
    subgraph Browser
        UI["React UI<br/>(Vite + Tailwind)"]
        Store["zustand store"]
        WSHook["useStatsWebSocket"]
    end

    subgraph Backend["FastAPI Backend"]
        API["REST / WS handlers<br/>(server.py)"]
        VP["VideoProcessor<br/>(worker thread)"]
        Det["YoloDetector"]
        DM["DistanceMonitor"]
        Vis["Visualizer"]
    end

    subgraph External
        Cam["Webcam / Video file"]
        Model["yolov8n.pt"]
    end

    UI -- "REST /api/*" --> API
    UI -- "MJPEG /stream" --> API
    WSHook -- "WS /ws/events" --> API
    UI --> Store
    WSHook --> Store

    API --> VP
    VP --> Det
    VP --> DM
    VP --> Vis
    VP --> Cam
    Det --> Model
```

## 2. 클래스 다이어그램

```mermaid
classDiagram
    class YoloDetector {
        -model: YOLO
        -device: str
        +__init__(model_path, device)
        +detect(frame, conf_threshold) tuple
    }

    class DistanceMonitor {
        +safe_distance: float
        -_safe_distance_sq: float
        +__init__(safe_distance)
        +check_distances(boxes, centers) tuple
    }

    class Visualizer {
        +COLOR_SAFE
        +COLOR_UNSAFE
        +FONT
        +draw_results(frame, boxes, confs, centers, pairs, count) ndarray
    }

    class VideoProcessor {
        -_detector: YoloDetector
        -_distance_monitor: DistanceMonitor
        -_visualizer: Visualizer
        -_default_source
        -_state_lock: Lock
        -_config: dict
        -_latest_jpeg: bytes
        -_stats: dict
        -_error: str
        -_pending_source
        -_current_source
        -_stop_event: Event
        -_pause_event: Event
        -_frame_ready: Event
        -_thread: Thread
        +start()
        +stop()
        +pause()
        +resume()
        +update_config(safe_distance, conf_threshold) dict
        +set_source(kind, value)
        +get_stats() dict
        +get_config() dict
        +get_source() dict
        +get_latest_jpeg() bytes
        +stream_jpeg() Iterator
        -_resolve_source(kind, value)
        -_open_capture(kind, value)
        -_run()
        -_loop()
    }

    class FastAPIApp {
        +lifespan()
        +get_stats()
        +post_config(ConfigPayload)
        +post_source(SourcePayload)
        +upload_video(file)
        +post_control(ControlPayload)
        +stream()
        +ws_events(ws)
    }

    class ConfigPayload {
        +safe_distance: float
        +conf_threshold: float
    }

    class SourcePayload {
        +kind: str
        +value: str
    }

    class ControlPayload {
        +action: str
    }

    VideoProcessor --> YoloDetector
    VideoProcessor --> DistanceMonitor
    VideoProcessor --> Visualizer
    FastAPIApp --> VideoProcessor
    FastAPIApp ..> ConfigPayload
    FastAPIApp ..> SourcePayload
    FastAPIApp ..> ControlPayload
```

## 3. 시퀀스 다이어그램 — 프레임 처리 루프

```mermaid
sequenceDiagram
    participant Thread as VideoProcessor thread
    participant Cap as cv2.VideoCapture
    participant Det as YoloDetector
    participant DM as DistanceMonitor
    participant Vis as Visualizer
    participant State as shared state (lock)

    loop every frame
        Thread->>Thread: check _pending_source / pause
        Thread->>Cap: read()
        Cap-->>Thread: frame
        Thread->>Thread: cv2.resize(640x480)
        Thread->>State: snapshot config (lock)
        State-->>Thread: safe_distance, conf_threshold
        Thread->>Det: detect(frame, conf)
        Det-->>Thread: boxes, confs, centers
        Thread->>DM: check_distances(boxes, centers)
        DM-->>Thread: unsafe_pairs, count
        Thread->>Vis: draw_results(...)
        Vis-->>Thread: annotated frame
        Thread->>Thread: cv2.imencode('.jpg', q=70)
        Thread->>State: update _latest_jpeg, _stats (lock)
        Thread->>Thread: set _frame_ready
    end
```

## 4. 시퀀스 다이어그램 — 비디오 업로드 플로우

```mermaid
flowchart TD
    A[User picks file and clicks Apply] --> B[POST api upload]
    B --> C[Server saves chunks to uploads dir]
    C --> D[Return upload id]
    D --> E[POST api source with upload id]
    E --> F[VideoProcessor sets pending source]
    F --> G[Worker thread releases old capture]
    G --> H[Worker opens new capture from uploads]
    H --> I[Frontend bumps stream key]
    I --> J[Browser reconnects to stream]
    J --> K[MJPEG plays new source]
```

## 5. 시퀀스 다이어그램 — 실시간 통계 갱신

```mermaid
sequenceDiagram
    participant UI as React UI
    participant Hook as useStatsWebSocket
    participant WS as /ws/events
    participant VP as VideoProcessor
    participant Store as zustand store

    UI->>Hook: mount
    Hook->>WS: connect
    WS-->>Hook: accepted
    Hook->>Store: setWsConnected(true)

    loop every 33ms
        WS->>VP: get_stats() + get_config()
        VP-->>WS: {stats, config}
        WS-->>Hook: send_json(payload)
        Hook->>Store: setStats(...), setConfig(...)
        Store-->>UI: re-render StatsPanel
    end

    WS-->>Hook: close
    Hook->>Store: setWsConnected(false)
    Hook->>Hook: setTimeout(reconnect, 1000)
```

## 6. 상태 다이어그램 — VideoProcessor

```mermaid
stateDiagram-v2
    [*] --> Idle: __init__
    Idle --> Running: start()
    Running --> Paused: pause()
    Paused --> Running: resume()
    Running --> Switching: set_source()
    Switching --> Running: capture reopened
    Running --> Error: exception in loop
    Paused --> Error: exception in loop
    Error --> [*]: stop()
    Running --> [*]: stop()
    Paused --> [*]: stop()
```

## 7. 배포 다이어그램

```mermaid
flowchart LR
    subgraph Dev["Development"]
        direction LR
        Vite["Vite dev<br/>:5173"]
        Uvi1["uvicorn<br/>:8000"]
        Vite -- proxy /api /stream /ws --> Uvi1
    end

    subgraph Prod["Production (선택)"]
        direction LR
        Uvi2["uvicorn<br/>:8000<br/>+ StaticFiles(dist/)"]
    end

    Dev -. 빌드 .-> Prod
```

## 8. 데이터 구조

```mermaid
classDiagram
    class Stats {
        +frame_id: int
        +people: int
        +unsafe: int
        +fps: float
        +error: str?
        +paused: bool
    }

    class Config {
        +safe_distance: float
        +conf_threshold: float
    }

    class Source {
        +kind: "default"|"upload"|"webcam"|"file"
        +value: str?
    }

    class StatsResponse {
        +stats: Stats
        +config: Config
        +source: Source
    }

    StatsResponse --> Stats
    StatsResponse --> Config
    StatsResponse --> Source
```
