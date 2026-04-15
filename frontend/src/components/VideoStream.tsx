import { useAppStore } from "../store/useAppStore";

export function VideoStream() {
  const streamKey = useAppStore((s) => s.streamKey);
  return (
    <div className="bg-black rounded-lg overflow-hidden shadow-lg aspect-[4/3] flex items-center justify-center">
      <img
        src={`/stream?k=${streamKey}`}
        alt="stream"
        className="w-full h-full object-contain"
      />
    </div>
  );
}
