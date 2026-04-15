import { useAppStore } from "../store/useAppStore";

function Card({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <div className="text-xs uppercase tracking-wider text-slate-400">{label}</div>
      <div className={`text-3xl font-bold mt-1 ${accent ?? "text-slate-100"}`}>{value}</div>
    </div>
  );
}

export function StatsPanel() {
  const stats = useAppStore((s) => s.stats);
  const wsConnected = useAppStore((s) => s.wsConnected);
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs">
        <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-emerald-400" : "bg-slate-500"}`} />
        <span className="text-slate-400">{wsConnected ? "Live" : "Disconnected"}</span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Card label="People" value={stats.people} />
        <Card label="Unsafe" value={stats.unsafe} accent="text-red-400" />
        <Card label="FPS" value={stats.fps.toFixed(1)} />
      </div>
      {stats.error && (
        <div className="bg-red-900/50 border border-red-700 text-red-200 text-sm p-2 rounded">
          {stats.error}
        </div>
      )}
    </div>
  );
}
