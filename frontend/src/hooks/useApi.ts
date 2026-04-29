import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type AsyncState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<AsyncState<T>>({ loading: true });
  const loaderRef = useRef(loader);
  const dependencyKey = useMemo(() => JSON.stringify(deps), [deps]);

  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  const refresh = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: undefined }));
    try {
      const data = await loaderRef.current();
      setState({ data, loading: false });
    } catch (error) {
      setState({ loading: false, error: error instanceof Error ? error.message : "Unknown error" });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, dependencyKey]);

  return { ...state, refresh };
}
