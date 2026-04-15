import { useState, useEffect } from "react";
import { useAppStore } from "../store/useAppStore";
import { useDebouncedConfigPush } from "../hooks/useDebouncedConfig";
import { sendControl } from "../lib/api";

export function Controls() {
  const serverConfig = useAppStore((s) => s.config);
  const status = useAppStore((s) => s.status);
  const setStatus = useAppStore((s) => s.setStatus);
  const bumpStream = useAppStore((s) => s.bumpStream);

  const [local, setLocal] = useState(serverConfig);

  useEffect(() => {
    setLocal(serverConfig);
  }, [serverConfig.safe_distance, serverConfig.conf_threshold]);

  useDebouncedConfigPush(local);

  const onControl = async (action: "play" | "pause" | "stop") => {
    await sendControl(action);
    setStatus(action === "play" ? "playing" : action === "pause" ? "paused" : "stopped");
    if (action === "play") bumpStream();
  };

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 space-y-4">
      <h3 className="text-sm font-semibold text-slate-300">Controls</h3>

      <div>
        <label className="flex justify-between text-xs text-slate-400">
          <span>Safe distance (px)</span>
          <span className="text-slate-200">{local.safe_distance.toFixed(0)}</span>
        </label>
        <input
          type="range"
          min={30}
          max={200}
          step={1}
          value={local.safe_distance}
          onChange={(e) => setLocal({ ...local, safe_distance: Number(e.target.value) })}
          className="w-full accent-emerald-500"
        />
      </div>

      <div>
        <label className="flex justify-between text-xs text-slate-400">
          <span>Confidence</span>
          <span className="text-slate-200">{local.conf_threshold.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min={0.1}
          max={0.9}
          step={0.05}
          value={local.conf_threshold}
          onChange={(e) => setLocal({ ...local, conf_threshold: Number(e.target.value) })}
          className="w-full accent-emerald-500"
        />
      </div>

      <div className="flex gap-2 pt-2">
        <button
          onClick={() => onControl("play")}
          className="flex-1 bg-emerald-600 hover:bg-emerald-500 rounded px-3 py-2 text-sm font-medium disabled:opacity-40"
          disabled={status === "playing"}
        >
          Play
        </button>
        <button
          onClick={() => onControl("pause")}
          className="flex-1 bg-amber-600 hover:bg-amber-500 rounded px-3 py-2 text-sm font-medium disabled:opacity-40"
          disabled={status === "paused"}
        >
          Pause
        </button>
        <button
          onClick={() => onControl("stop")}
          className="flex-1 bg-slate-600 hover:bg-slate-500 rounded px-3 py-2 text-sm font-medium"
        >
          Stop
        </button>
      </div>
    </div>
  );
}
