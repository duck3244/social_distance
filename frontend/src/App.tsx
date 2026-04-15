import { useEffect } from "react";
import { VideoStream } from "./components/VideoStream";
import { StatsPanel } from "./components/StatsPanel";
import { Controls } from "./components/Controls";
import { SourceSelector } from "./components/SourceSelector";
import { useStatsWebSocket } from "./hooks/useWebSocket";
import { fetchStats } from "./lib/api";
import { useAppStore } from "./store/useAppStore";

function App() {
  useStatsWebSocket();
  const setStats = useAppStore((s) => s.setStats);
  const setConfig = useAppStore((s) => s.setConfig);

  useEffect(() => {
    fetchStats()
      .then((d) => {
        setStats(d.stats);
        setConfig(d.config);
      })
      .catch(() => {});
  }, [setStats, setConfig]);

  return (
    <div className="min-h-screen p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Social Distance Monitor</h1>
        <p className="text-sm text-slate-400">Real-time YOLOv8 distance monitoring</p>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6 max-w-7xl mx-auto">
        <VideoStream />
        <div className="space-y-4">
          <StatsPanel />
          <Controls />
          <SourceSelector />
        </div>
      </div>
    </div>
  );
}

export default App;
