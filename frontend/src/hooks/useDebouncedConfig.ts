import { useEffect, useRef } from "react";
import { updateConfig } from "../lib/api";
import type { Config } from "../lib/api";

export function useDebouncedConfigPush(config: Config, delay = 300) {
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const t = setTimeout(() => {
      updateConfig(config).catch(() => {});
    }, delay);
    return () => clearTimeout(t);
  }, [config, delay]);
}
