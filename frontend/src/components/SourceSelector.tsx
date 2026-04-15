import { useState } from "react";
import { setSource, uploadVideo } from "../lib/api";
import { useAppStore } from "../store/useAppStore";

type Mode = "default" | "upload" | "webcam";

export function SourceSelector() {
  const [mode, setMode] = useState<Mode>("default");
  const [webcamIndex, setWebcamIndex] = useState("0");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bumpStream = useAppStore((s) => s.bumpStream);

  const apply = async () => {
    setError(null);
    setBusy(true);
    try {
      if (mode === "default") {
        await setSource("default");
      } else if (mode === "webcam") {
        await setSource("webcam", webcamIndex);
      } else {
        if (!file) {
          setError("Pick a video file first");
          return;
        }
        const { upload_id } = await uploadVideo(file);
        await setSource("upload", upload_id);
      }
      setTimeout(bumpStream, 500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 space-y-3">
      <h3 className="text-sm font-semibold text-slate-300">Source</h3>

      <div className="space-y-2 text-sm">
        <label className="flex items-center gap-2">
          <input type="radio" checked={mode === "default"} onChange={() => setMode("default")} />
          Default video
        </label>

        <label className="flex items-center gap-2">
          <input type="radio" checked={mode === "upload"} onChange={() => setMode("upload")} />
          Upload
        </label>
        {mode === "upload" && (
          <div className="pl-6 space-y-1">
            <input
              type="file"
              accept="video/*,.mp4,.avi,.mov,.mkv,.webm"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-xs w-full file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-slate-700 file:text-slate-200 hover:file:bg-slate-600"
            />
            {file && (
              <div className="text-xs text-slate-400 truncate">
                {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
              </div>
            )}
          </div>
        )}

        <label className="flex items-center gap-2">
          <input type="radio" checked={mode === "webcam"} onChange={() => setMode("webcam")} />
          Webcam
        </label>
        {mode === "webcam" && (
          <div className="pl-6 flex gap-2 items-center">
            <span className="text-slate-400 text-xs">Device index</span>
            <input
              type="number"
              min={0}
              value={webcamIndex}
              onChange={(e) => setWebcamIndex(e.target.value)}
              className="w-20 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
            />
          </div>
        )}
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-900/30 border border-red-800 rounded px-2 py-1">
          {error}
        </div>
      )}

      <button
        onClick={apply}
        disabled={busy}
        className="w-full bg-sky-600 hover:bg-sky-500 rounded px-3 py-2 text-sm font-medium disabled:opacity-50"
      >
        {busy ? "Applying..." : "Apply"}
      </button>
    </div>
  );
}
