import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { SystemItem } from '../services/types';
import { fetchSystems } from '../services/api';

interface SystemsContextValue {
  systems: SystemItem[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const SystemsContext = createContext<SystemsContextValue | undefined>(undefined);

export function SystemsProvider({ children }: { children: ReactNode }) {
  const [systems, setSystems] = useState<SystemItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchSystems();
      setSystems(data);
      setError(null);
    } catch {
      setError('Failed to load systems');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<SystemsContextValue>(
    () => ({ systems, loading, error, refresh }),
    [systems, loading, error, refresh],
  );

  return <SystemsContext.Provider value={value}>{children}</SystemsContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSystems(): SystemsContextValue {
  const ctx = useContext(SystemsContext);
  if (!ctx) throw new Error('useSystems must be used within a SystemsProvider');
  return ctx;
}
